from django.urls import include, path
from rest_framework.routers import DefaultRouter

from finance import views

router = DefaultRouter()
router.register('frais', views.FraisViewSet, basename='finance-frais')
router.register('paie', views.PaieViewSet, basename='finance-paie')
router.register('operations', views.OperationViewSet, basename='finance-operation')
router.register('tarifs', views.TarifViewSet, basename='finance-tarif')

urlpatterns = [
    path('tableau-de-bord/', views.TableauDeBordView.as_view(), name='finance_tableau_de_bord'),
    path('paiements/<int:pk>/annuler/', views.AnnulerPaiementView.as_view(), name='finance_annuler_paiement'),
    path('paiements/<int:pk>/recu.pdf', views.RecuPaiementView.as_view(), name='finance_recu_paiement'),
    path('paiements-paie/<int:pk>/annuler/', views.AnnulerPaiementPaieView.as_view(), name='finance_annuler_paiement_paie'),
    path('paiements-paie/<int:pk>/recu.pdf', views.RecuPaiementPaieView.as_view(), name='finance_recu_paiement_paie'),
    path('operations/<int:pk>/recu.pdf', views.RecuOperationView.as_view(), name='finance_recu_operation'),
    path('', include(router.urls)),
]

# Espace étudiant, servi sous /api/scolarite/moi/frais/ (voir config/urls.py).
urlpatterns_etudiant = [
    path('', views.MesFraisView.as_view(), name='finance_moi_frais'),
    path('paiements/<int:pk>/recu.pdf', views.MonRecuView.as_view(), name='finance_moi_recu'),
]
