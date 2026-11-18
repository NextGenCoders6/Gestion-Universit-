"""Connexion unique de l'ERP (JWT).

Repris de uccb_backend/EDT_app/authentication.py : refus des profils
suspendus à la connexion et au renouvellement. Le jeton ne porte que
l'identité ; les droits sont relus via /api/core/moi/, pour qu'un retrait de
droit prenne effet sans attendre l'expiration du jeton.
"""
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from core.droits import faculte_rattachee, modules_accessibles, roles_contextuels
from core.permissions import message_suspension, personne_suspendue
from core.throttles import LoginCompteRateThrottle, LoginIPRateThrottle


def nom_complet(user):
    personne = getattr(user, 'personne', None)
    if personne is not None:
        return personne.nom_complet
    return user.get_full_name() or user.username


def construire_moi(user, request=None):
    personne = getattr(user, 'personne', None)
    photo = None
    if personne is not None and personne.photo:
        photo = request.build_absolute_uri(personne.photo.url) if request else personne.photo.url
    fac = faculte_rattachee(user)
    return {
        'id': user.pk,
        'username': user.username,
        'nom_complet': nom_complet(user),
        'photo': photo,
        'personne_id': personne.pk if personne is not None else None,
        'modules': modules_accessibles(user),
        'roles': roles_contextuels(user),
        'faculte_rattachee': {'id': fac.pk, 'code': fac.code, 'nom': fac.nom} if fac else None,
    }


class ProfilSuspenduAuth(AuthenticationFailed):
    def __init__(self, motif):
        super().__init__(detail={'detail': message_suspension(motif), 'code': 'profil_suspendu'})


class ConnexionSerializer(TokenObtainPairSerializer):
    default_error_messages = {'no_active_account': 'Identifiant ou mot de passe incorrect.'}

    def validate(self, attrs):
        data = super().validate(attrs)
        personne = personne_suspendue(self.user)
        if personne is not None:
            raise ProfilSuspenduAuth(personne.motif_suspension)
        data['user'] = construire_moi(self.user, self.context.get('request'))
        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['nom_complet'] = nom_complet(user)
        return token


class RenouvellementSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            user_id = RefreshToken(attrs['refresh']).get('user_id')
        except TokenError:
            user_id = None  # laissé au serializer parent, qui renvoie l'erreur standard
        if user_id is not None:
            user = get_user_model().objects.filter(pk=user_id).first()
            personne = personne_suspendue(user) if user else None
            if personne is not None:
                raise ProfilSuspenduAuth(personne.motif_suspension)
        return super().validate(attrs)


class ConnexionView(TokenObtainPairView):
    serializer_class = ConnexionSerializer
    throttle_classes = [LoginCompteRateThrottle, LoginIPRateThrottle]


class RenouvellementView(TokenRefreshView):
    serializer_class = RenouvellementSerializer


class MoiView(APIView):
    def get(self, request):
        return Response(construire_moi(request.user, request))


class DeconnexionView(APIView):
    # Possible même pour un profil suspendu : invalider son refresh token est souhaitable.
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            RefreshToken(request.data.get('refresh', '')).blacklist()
        except TokenError:
            pass  # jeton déjà invalide : la déconnexion est acquise
        return Response(status=status.HTTP_205_RESET_CONTENT)
