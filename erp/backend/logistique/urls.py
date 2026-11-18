from django.urls import include, path
from rest_framework.routers import DefaultRouter

from logistique import views

router = DefaultRouter()
router.register('bus', views.BusViewSet, basename='logistique-bus')
router.register('trajets', views.TrajetViewSet, basename='logistique-trajet')
router.register('affectations', views.AffectationViewSet, basename='logistique-affectation')

urlpatterns = [
    path('tableau-de-bord/', views.TableauDeBordView.as_view(), name='logistique_tableau_de_bord'),
    path('chauffeurs/', views.ChauffeursView.as_view(), name='logistique_chauffeurs'),
    path('couts/', views.CoutsView.as_view(), name='logistique_couts'),
    path('', include(router.urls)),
]
