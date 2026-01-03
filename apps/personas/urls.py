"""Django ATS - Personas URLs"""
from django.urls import path

from .views import (
    PersonaListView,
    PersonaDetailView,
    PersonaCreateView,
    PersonaUpdateView,
    PersonaDeleteView,
    PersonaDuplicateView,
    PersonaToggleActiveView,
)

app_name = 'personas'

urlpatterns = [
    path('', PersonaListView.as_view(), name='persona_list'),
    path('create/', PersonaCreateView.as_view(), name='persona_create'),
    path('<uuid:pk>/', PersonaDetailView.as_view(), name='persona_detail'),
    path('<uuid:pk>/edit/', PersonaUpdateView.as_view(), name='persona_update'),
    path('<uuid:pk>/delete/', PersonaDeleteView.as_view(), name='persona_delete'),
    path('<uuid:pk>/duplicate/', PersonaDuplicateView.as_view(), name='persona_duplicate'),
    path('<uuid:pk>/toggle-active/', PersonaToggleActiveView.as_view(), name='persona_toggle_active'),
]
