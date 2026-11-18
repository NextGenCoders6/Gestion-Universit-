from django.urls import include, path
from rest_framework.routers import DefaultRouter

from scolarite import views_faculte, views_secretariat

router = DefaultRouter()
router.register('etudiants', views_secretariat.EtudiantViewSet, basename='scolarite-etudiant')
router.register('inscriptions', views_secretariat.InscriptionViewSet, basename='scolarite-inscription')

urlpatterns = [
    path('etudiants/<int:pk>/notes/', views_faculte.NotesEtudiantView.as_view(), name='scolarite_notes_etudiant'),
    path('saisie/', views_faculte.SaisieView.as_view(), name='scolarite_saisie'),
    path('deliberation/', views_faculte.DeliberationView.as_view(), name='scolarite_deliberation'),
    path('deliberation/excel/', views_faculte.DeliberationExcelView.as_view(), name='scolarite_deliberation_excel'),
    path('promotion/', views_faculte.PromotionView.as_view(), name='scolarite_promotion'),
    path('orientation/', views_faculte.OrientationView.as_view(), name='scolarite_orientation'),
    path('', include(router.urls)),
]
