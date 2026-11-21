from django.urls import include, path
from rest_framework.routers import DefaultRouter

from core.api import referentiel as ref
from core.api.activation import ActivationView
from core.api.etablissement import EtablissementView
from core.api.personnes import PersonneViewSet
from core.api.utilisateurs import AuditViewSet, ModulesView, UtilisateurViewSet
from core.auth import ConnexionView, DeconnexionView, MoiView, RenouvellementView

router = DefaultRouter()
router.register('annees', ref.AnneeViewSet, basename='annee')
router.register('periodes', ref.PeriodeViewSet, basename='periode')
router.register('facultes', ref.FaculteViewSet, basename='faculte')
router.register('departements', ref.DepartementViewSet, basename='departement')
router.register('portails', ref.PortailViewSet, basename='portail')
router.register('filieres', ref.FiliereViewSet, basename='filiere')
router.register('parcours', ref.ParcoursViewSet, basename='parcours')
router.register('classes', ref.ClasseViewSet, basename='classe')
router.register('ues', ref.UEViewSet, basename='ue')
router.register('ecs', ref.ECViewSet, basename='ec')
router.register('personnes', PersonneViewSet, basename='personne')
router.register('utilisateurs', UtilisateurViewSet, basename='utilisateur')
router.register('audit', AuditViewSet, basename='audit')

urlpatterns = [
    path('token/', ConnexionView.as_view(), name='core_token'),
    path('token/refresh/', RenouvellementView.as_view(), name='core_token_refresh'),
    path('deconnexion/', DeconnexionView.as_view(), name='core_deconnexion'),
    path('moi/', MoiView.as_view(), name='core_moi'),
    path('activation/', ActivationView.as_view(), name='core_activation'),
    path('modules/', ModulesView.as_view(), name='core_modules'),
    path('etablissement/', EtablissementView.as_view(), name='core_etablissement'),
    path('', include(router.urls)),
]
