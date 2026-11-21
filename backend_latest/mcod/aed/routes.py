"""AED API routes – appended to mcod.routes.routes only when settings.AED_ENABLED is True."""

from mcod.aed import views

routes = [
    ("/aed/schema", views.AedSchemaView()),
    ("/aed/template.csv", views.AedTemplateView("csv")),
    ("/aed/template.xlsx", views.AedTemplateView("xlsx")),
    ("/aed/validate", views.AedValidateView()),
    ("/aed/reports/{id:int}", views.AedResourceReportView()),
    ("/aed/config", views.AedConfigView()),
]
