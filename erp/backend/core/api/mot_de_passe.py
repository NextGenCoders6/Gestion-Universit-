"""Mot de passe oublié : lien de réinitialisation envoyé par e-mail.

Les réponses publiques ne révèlent jamais si un compte correspond à la saisie.
"""
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import journaliser
from core.auth import nom_complet
from core.models import Personne
from core.permissions import personne_suspendue
from core.throttles import LoginIPRateThrottle, OubliRateThrottle

logger = logging.getLogger(__name__)

MESSAGE_DEMANDE = "Si un compte correspond, un e-mail contenant un lien vient d'être envoyé."
SUJET = 'UCCB — Réinitialisation de votre mot de passe'
CORPS = """Bonjour {nom},

Pour choisir un nouveau mot de passe, ouvrez ce lien (valable 1 heure) :
{lien}

Si vous n'avez rien demandé, ignorez ce message.
"""


def compte_pour_identifiant(saisie):
    """Compte désigné par un identifiant de connexion, sinon par une adresse e-mail."""
    saisie = (saisie or '').strip()
    if not saisie:
        return None
    user = User.objects.filter(username__iexact=saisie).first()
    if user is None:
        personne = Personne.objects.filter(email__iexact=saisie, user__isnull=False).select_related('user').first()
        user = personne.user if personne else None
    if user is None:
        user = User.objects.filter(email__iexact=saisie).order_by('pk').first()
    return user


def adresse_de(user):
    personne = getattr(user, 'personne', None)
    return (personne.email if personne else None) or user.email or None


def lien_reinitialisation(user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    return f'{settings.BASE_URL}/reinitialisation/{uid}/{default_token_generator.make_token(user)}'


class DemandeReinitialisationView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [OubliRateThrottle, LoginIPRateThrottle]

    def post(self, request):
        user = compte_pour_identifiant(str(request.data.get('identifiant', '')))
        adresse = adresse_de(user) if user else None
        if user is not None and user.is_active and personne_suspendue(user) is None and adresse:
            corps = CORPS.format(nom=nom_complet(user), lien=lien_reinitialisation(user))
            try:
                send_mail(SUJET, corps, None, [adresse])
            except Exception:
                logger.exception("Échec de l'envoi du lien de réinitialisation à %s", user.username)
            else:
                journaliser(request, 'core', 'demande_reinitialisation', user.username)
        return Response({'detail': MESSAGE_DEMANDE})
