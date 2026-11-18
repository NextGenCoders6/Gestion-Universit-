from django.urls import include, path
from rest_framework.routers import DefaultRouter

from scolarite import views_secretariat

router = DefaultRouter()
router.register('etudiants', views_secretariat.EtudiantViewSet, basename='scolarite-etudiant')
router.register('inscriptions', views_secretariat.InscriptionViewSet, basename='scolarite-inscription')

urlpatterns = [
    path('', include(router.urls)),
]
