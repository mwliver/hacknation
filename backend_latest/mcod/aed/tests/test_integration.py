import io
import json
import os
import uuid

import falcon
import pytest
from django.core.files.base import ContentFile
from django.test import override_settings
from openpyxl import load_workbook

from mcod.aed import admin as aed_admin, schema
from mcod.aed.models import AedValidationReport
from mcod.aed.services import ensure_aed_tags, report_summary, validate_resource
from mcod.aed.tasks import schedule_aed_validation
from mcod.resources.factories import ResourceFactory
from mcod.resources.models import Resource
from mcod.tags.models import Tag

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures", "validation")


def _fixture(name: str) -> bytes:
    with open(os.path.join(FIXTURES, name), "rb") as f:
        return f.read()


def _multipart(filename: str, content: bytes, field: str = "file"):
    boundary = "aedboundary" + uuid.uuid4().hex
    body = (
        (
            f'--{boundary}\r\nContent-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n"
        ).encode()
        + content
        + f"\r\n--{boundary}--\r\n".encode()
    )
    return body, {"Content-Type": f"multipart/form-data; boundary={boundary}"}


@pytest.fixture
def aed_resource(mocker):
    mocker.patch("mcod.aed.tasks.validate_aed_resource_task.apply_async_on_commit")
    resource = ResourceFactory.create(status="published")
    main = resource.files.first()
    main.file.save("aed_otwock.csv", ContentFile(_fixture("enum_value.csv")), save=True)
    Resource.raw.filter(pk=resource.pk).update(data_standard="AED_V1")
    return Resource.raw.get(pk=resource.pk)


# ---------------------------------------------------------------------------------------------------------------
# Services, tasks, signals
# ---------------------------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_validate_resource_stores_report(aed_resource):
    report = validate_resource(aed_resource)
    assert AedValidationReport.objects.filter(resource=aed_resource).count() == 1
    assert not report.is_compliant
    assert report.errors_count == 1
    assert report.issues[0]["kod"] == "ENUM_VALUE"
    summary = report_summary(aed_resource)
    assert summary["zgodny"] is False and summary["liczba_bledow"] == 1


@pytest.mark.django_db
def test_report_summary_for_not_validated_and_other_resources(aed_resource):
    assert report_summary(aed_resource) == {"standard": "AED_V1", "zgodny": None}
    other = ResourceFactory.create()
    assert report_summary(other) is None


@pytest.mark.django_db
def test_schedule_only_for_aed_resources(aed_resource, mocker):
    apply = mocker.patch("mcod.aed.tasks.validate_aed_resource_task.apply_async_on_commit")
    other = ResourceFactory.create()
    assert schedule_aed_validation(other) is False
    assert schedule_aed_validation(aed_resource) is True
    apply.assert_called_once_with(args=(aed_resource.pk,))
    assert schedule_aed_validation(aed_resource.pk) is True
    assert schedule_aed_validation(other.pk) is False
    with override_settings(AED_ENABLED=False):
        assert schedule_aed_validation(aed_resource) is False


@pytest.mark.django_db
def test_marking_resource_as_aed_tags_dataset_and_validates(mocker):
    apply = mocker.patch("mcod.aed.tasks.validate_aed_resource_task.apply_async_on_commit")
    resource = ResourceFactory.create()
    assert not resource.dataset.tags.filter(name="AED").exists()
    resource = Resource.objects.get(pk=resource.pk)
    resource.data_standard = "AED_V1"
    resource.save()
    assert set(resource.dataset.tags.filter(name="AED").values_list("language", flat=True)) == {"pl", "en"}
    apply.assert_called_once_with(args=(resource.pk,))
    ensure_aed_tags(resource.dataset)  # idempotent
    assert Tag.objects.filter(name="AED").count() == 2


@pytest.mark.django_db
def test_validate_task_skips_other_resources():
    from mcod.aed.tasks import validate_aed_resource_task

    other = ResourceFactory.create()
    assert validate_aed_resource_task(other.pk) == {"resource_id": other.pk, "skipped": True}
    assert not AedValidationReport.objects.exists()


# ---------------------------------------------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_helpers(aed_resource):
    fieldsets = aed_admin.resource_fieldsets([], aed_resource)
    fields = [f for _, opts in fieldsets for f in opts["fields"]]
    assert fields == ["data_standard", "aed_validation_report"]
    assert aed_admin.resource_tabs(aed_resource) == [("aed", aed_admin.resource_tabs(aed_resource)[0][1])]
    assert "aed_validation_report" in aed_admin.resource_readonly_fields(aed_resource)

    html = str(aed_admin.aed_validation_report(None, aed_resource))
    assert "AED v1" in html  # "not validated yet" message
    validate_resource(aed_resource)
    html = str(aed_admin.aed_validation_report(None, aed_resource))
    assert "ENUM_VALUE" in html and "status_urzadzenia" in html


@pytest.mark.django_db
def test_admin_helpers_disabled(aed_resource):
    with override_settings(AED_ENABLED=False):
        assert aed_admin.resource_fieldsets(("x",), aed_resource) == ("x",)
        assert aed_admin.resource_tabs(aed_resource) == []
        assert aed_admin.resource_readonly_fields(aed_resource) == ()


@pytest.mark.django_db
def test_admin_resource_change_page_has_aed_tab(admin, aed_resource):
    from django.test import Client

    client = Client()
    client.force_login(admin)
    validate_resource(aed_resource)
    response = client.get(f"/resources/resource/{aed_resource.pk}/change/")
    assert response.status_code == 200
    content = response.content.decode()
    assert "suit-tab-aed" in content
    assert 'name="data_standard"' in content


# ---------------------------------------------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------------------------------------------


def test_api_schema(client14):
    resp = client14.simulate_get("/1.4/aed/schema")
    assert resp.status == falcon.HTTP_200
    assert resp.json == schema.load_schema()


def test_api_template_csv(client14):
    resp = client14.simulate_get("/1.4/aed/template.csv")
    assert resp.status == falcon.HTTP_200
    assert resp.headers["content-type"].startswith("text/csv")
    assert resp.content.decode("utf-8").splitlines() == [",".join(schema.all_field_names())]
    with_examples = client14.simulate_get("/1.4/aed/template.csv", params={"przyklady": "true"})
    assert len(with_examples.content.decode("utf-8").splitlines()) == 4


def test_api_template_xlsx(client14):
    resp = client14.simulate_get("/1.4/aed/template.xlsx")
    assert resp.status == falcon.HTTP_200
    assert "attachment" in resp.headers["content-disposition"]
    wb = load_workbook(io.BytesIO(resp.content))
    assert wb.sheetnames[0] == "dane"


def test_api_config(client14):
    resp = client14.simulate_get("/1.4/aed/config")
    assert resp.status == falcon.HTTP_200
    attrs = resp.json["data"]["attributes"]
    assert resp.json["data"]["type"] == "aed_config"
    assert attrs["enabled"] is True and attrs["campaign_name"] and attrs["standard"] == "AED_V1"


@pytest.mark.django_db
def test_api_validate_valid_file_saves_nothing(client14):
    resources_before = Resource.raw.count()
    body, headers = _multipart("aed.csv", _fixture("valid.csv"))
    resp = client14.simulate_post("/1.4/aed/validate", body=body, headers=headers)
    assert resp.status == falcon.HTTP_200, resp.text
    data = resp.json["data"]
    assert data["type"] == "aed_validation_report"
    assert data["attributes"]["zgodny"] is True
    assert data["attributes"]["liczba_wierszy"] == 3
    assert data["attributes"]["problemy"] == []
    assert not AedValidationReport.objects.exists()
    assert Resource.raw.count() == resources_before


@pytest.mark.django_db
def test_api_validate_file_with_errors(client14):
    body, headers = _multipart("aed.csv", _fixture("duplicate_id.csv"))
    attrs = client14.simulate_post("/1.4/aed/validate", body=body, headers=headers).json["data"]["attributes"]
    assert attrs["zgodny"] is False
    assert attrs["problemy"][0] == {
        "wiersz": 3,
        "kolumna": "id_aed",
        "kod": "DUPLICATE_ID",
        "poziom": "ERROR",
        "komunikat_pl": attrs["problemy"][0]["komunikat_pl"],
        "komunikat_en": attrs["problemy"][0]["komunikat_en"],
    }


@pytest.mark.django_db
def test_api_validate_never_returns_forbidden_values(client14):
    rows = _fixture("valid.csv").decode().splitlines()
    rows[0] += ",kod_szafki"
    rows[1:] = [r + ",4321" for r in rows[1:]]
    body, headers = _multipart("aed.csv", "\n".join(rows).encode())
    resp = client14.simulate_post("/1.4/aed/validate", body=body, headers=headers)
    assert resp.json["data"]["attributes"]["problemy"][0]["kod"] == "FORBIDDEN_COLUMN"
    assert "4321" not in resp.text


@pytest.mark.django_db
def test_api_validate_xlsx(client14):
    body, headers = _multipart("szablon.xlsx", client14.simulate_get("/1.4/aed/template.xlsx").content)
    resp = client14.simulate_post("/1.4/aed/validate", body=body, headers=headers)
    assert resp.json["data"]["attributes"]["zgodny"] is True


@pytest.mark.parametrize("filename", ["aed.pdf", "aed.xlsm", "aed"])
def test_api_validate_rejects_other_types(client14, filename):
    body, headers = _multipart(filename, b"anything")
    assert client14.simulate_post("/1.4/aed/validate", body=body, headers=headers).status == falcon.HTTP_422


def test_api_validate_requires_multipart_and_file_field(client14):
    assert client14.simulate_post("/1.4/aed/validate", json={}).status == falcon.HTTP_415
    body, headers = _multipart("aed.csv", b"x", field="other")
    assert client14.simulate_post("/1.4/aed/validate", body=body, headers=headers).status == falcon.HTTP_422


def test_api_validate_size_limit(client14):
    with override_settings(AED_VALIDATE_MAX_FILE_SIZE=100):
        body, headers = _multipart("aed.csv", _fixture("valid.csv"))
        assert client14.simulate_post("/1.4/aed/validate", body=body, headers=headers).status == falcon.HTTP_413


@pytest.mark.django_db
def test_api_resource_report(client14, aed_resource):
    assert client14.simulate_get(f"/1.4/aed/reports/{aed_resource.pk}").status == falcon.HTTP_404
    validate_resource(aed_resource)
    resp = client14.simulate_get(f"/1.4/aed/reports/{aed_resource.pk}")
    assert resp.status == falcon.HTTP_200
    attrs = resp.json["data"]["attributes"]
    assert attrs["zasob_id"] == aed_resource.pk and attrs["liczba_bledow"] == 1
    other = ResourceFactory.create(status="published")
    assert client14.simulate_get(f"/1.4/aed/reports/{other.pk}").status == falcon.HTTP_404


@pytest.mark.django_db
def test_resource_api_exposes_standard_and_status(client14, aed_resource):
    validate_resource(aed_resource)
    resp = client14.simulate_get(f"/1.4/resources/{aed_resource.pk}")
    assert resp.status == falcon.HTTP_200, resp.text
    attrs = resp.json["data"]["attributes"]
    assert attrs["data_standard"] == "AED_V1"
    assert attrs["aed_validation"]["zgodny"] is False
    assert json.dumps(attrs)  # serializable
