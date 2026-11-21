from django.urls import include, path
from rest_framework.routers import DefaultRouter

from scolarite import views_documents, views_etudiant, views_faculte, views_secretariat

router = DefaultRouter()
router.register('etudiants', views_secretariat.EtudiantViewSet, basename='scolarite-etudiant')
router.register('inscriptions', views_secretariat.InscriptionViewSet, basename='scolarite-inscription')

urlpatterns = [
    path('moi/notes/', views_etudiant.MesNotesView.as_view(), name='scolarite_moi_notes'),
    path('moi/planning/', views_etudiant.MonPlanningEtudiantView.as_view(), name='scolarite_moi_planning'),
    path('moi/enseignants/', views_etudiant.MesEnseignantsView.as_view(), name='scolarite_moi_enseignants'),
    path('etudiants/<int:pk>/notes/', views_faculte.NotesEtudiantView.as_view(), name='scolarite_notes_etudiant'),
    path('etudiants/<int:pk>/attestation.pdf', views_documents.AttestationView.as_view(),
         name='scolarite_attestation'),
    path('etudiants/<int:pk>/releve.pdf', views_documents.ReleveView.as_view(), name='scolarite_releve'),
    path('matrice-a3.pdf', views_documents.MatriceA3View.as_view(), name='scolarite_matrice_a3'),
    path('classes/', views_secretariat.ClassesView.as_view(), name='scolarite_classes'),
    path('saisie/', views_faculte.SaisieView.as_view(), name='scolarite_saisie'),
    path('deliberation/', views_faculte.DeliberationView.as_view(), name='scolarite_deliberation'),
    path('deliberation/excel/', views_faculte.DeliberationExcelView.as_view(), name='scolarite_deliberation_excel'),
    path('promotion/', views_faculte.PromotionView.as_view(), name='scolarite_promotion'),
    path('orientation/', views_faculte.OrientationView.as_view(), name='scolarite_orientation'),
    path('', include(router.urls)),
]
