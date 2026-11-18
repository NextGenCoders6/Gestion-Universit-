from django.urls import include, path
from rest_framework.routers import DefaultRouter

from edt import views

router = DefaultRouter()
router.register('seances', views.SeanceViewSet, basename='seance')
router.register('affectations', views.AffectationViewSet, basename='affectation')
router.register('referents', views.ReferentViewSet, basename='referent')
router.register('enseignants', views.EnseignantViewSet, basename='edt-enseignant')
router.register('documents', views.DocumentViewSet, basename='document')

urlpatterns = [
    path('enseignements/', views.EnseignementsView.as_view(), name='edt_enseignements'),
    path('moi/planning/', views.MonPlanningView.as_view(), name='edt_moi_planning'),
    path('moi/enseignements/', views.MesEnseignementsView.as_view(), name='edt_moi_enseignements'),
    path('moi/documents/', views.MesDocumentsView.as_view(), name='edt_moi_documents'),
    path('moi/documents/<int:pk>/telecharger/', views.MonDocumentTelechargementView.as_view(),
         name='edt_moi_document_telecharger'),
    path('', include(router.urls)),
]
