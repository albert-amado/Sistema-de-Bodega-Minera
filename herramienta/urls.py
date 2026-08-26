from django.urls import path

from . import views

app_name = "herramienta"

urlpatterns = [
    path("", views.HerramientaListView.as_view(), name="herramienta_list"),
    path(
        "<int:pk>/",
        views.HerramientaDetailView.as_view(),
        name="herramienta_detail",
    ),
    path(
        "categorias/",
        views.CategoriaHerramientaListView.as_view(),
        name="categoria_list",
    ),
    path(
        "categorias/<int:pk>/",
        views.CategoriaHerramientaDetailView.as_view(),
        name="categoria_detail",
    ),
    path(
        "traslados/",
        views.TrasladoListView.as_view(),
        name="traslado_list",
    ),
    path(
        "traslados/<int:pk>/",
        views.TrasladoDetailView.as_view(),
        name="traslado_detail",
    ),
    path(
        "detalles-traslado/",
        views.DetalleTrasladoListView.as_view(),
        name="detalle_traslado_list",
    ),
    path(
        "detalles-traslado/<int:pk>/",
        views.DetalleTrasladoDetailView.as_view(),
        name="detalle_traslado_detail",
    ),
]
