from django.urls import path

from core.auth import ConnexionView, DeconnexionView, MoiView, RenouvellementView

urlpatterns = [
    path('token/', ConnexionView.as_view(), name='core_token'),
    path('token/refresh/', RenouvellementView.as_view(), name='core_token_refresh'),
    path('deconnexion/', DeconnexionView.as_view(), name='core_deconnexion'),
    path('moi/', MoiView.as_view(), name='core_moi'),
]
