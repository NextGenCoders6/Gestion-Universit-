from django.urls import include, path
from rest_framework.routers import DefaultRouter

from rh import views

router = DefaultRouter()
router.register('enseignants', views.EnseignantViewSet, basename='rh-enseignant')
router.register('employes', views.EmployeViewSet, basename='rh-employe')
router.register('contrats', views.ContratViewSet, basename='rh-contrat')

urlpatterns = [
    path('tableau-de-bord/', views.TableauDeBordView.as_view(), name='rh_tableau_de_bord'),
    path('vacations/', views.VacationsView.as_view(), name='rh_vacations'),
    path('vacations/historique/', views.HistoriqueVacationsView.as_view(), name='rh_vacations_historique'),
    path('', include(router.urls)),
]
