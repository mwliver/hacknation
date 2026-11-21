from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from mcod.aed.models import DATA_STANDARD_AED_V1


@receiver(post_save, sender="resources.Resource", dispatch_uid="aed_resource_post_save")
def aed_resource_post_save(sender, instance, created, **kwargs):
    """
    When a resource becomes AED v1 (or is created as one): tag its dataset with "AED" and validate the file.
    A file change is validated by the regular resource pipeline (see entrypoint_res_file), so here we only
    react to changes of ``data_standard`` itself.
    """
    if not settings.AED_ENABLED or instance.data_standard != DATA_STANDARD_AED_V1 or kwargs.get("raw"):
        return
    from mcod.aed.services import ensure_aed_tags
    from mcod.aed.tasks import validate_aed_resource_task

    ensure_aed_tags(instance.dataset)
    tracker = getattr(instance, "tracker", None)
    changed = created or (tracker is not None and tracker.has_changed("data_standard"))
    if changed and not created and instance.main_file:
        validate_aed_resource_task.apply_async_on_commit(args=(instance.pk,))
