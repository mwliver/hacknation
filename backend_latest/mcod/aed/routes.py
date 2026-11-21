"""AED API routes – appended to mcod.routes.routes only when settings.AED_ENABLED is True."""

from mcod.aed import record_views, views

routes = [
    ("/aed", record_views.AedListView()),
    ("/aed/nearest", record_views.AedNearestView()),
    ("/aed/stats", record_views.AedStatsView()),
    ("/aed/schema", views.AedSchemaView()),
    ("/aed/template.csv", views.AedTemplateView("csv")),
    ("/aed/template.xlsx", views.AedTemplateView("xlsx")),
    ("/aed/validate", views.AedValidateView()),
    ("/aed/reports/{id:int}", views.AedResourceReportView()),
    ("/aed/config", views.AedConfigView()),
    ("/aed/{id:uuid}", record_views.AedDetailView()),
]
