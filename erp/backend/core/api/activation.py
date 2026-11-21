"""Activation du compte par l'étudiant ou l'enseignant lui-même.

La personne saisit les informations enregistrées par le secrétariat (étudiant)
ou les ressources humaines (enseignant), puis choisit son mot de passe. Son
identifiant de connexion est son matricule.
"""
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import journaliser
from core.models import Enseignant, Etudiant, Personne
from core.throttles import ActivationRateThrottle, LoginIPRateThrottle

ECHEC_ACTIVATION = 'Informations incorrectes ou compte déjà activé.'


class ActivationSerializer(serializers.Serializer):
    matricule = serializers.CharField(max_length=35)
    email = serializers.EmailField()
    date_naissance = serializers.DateField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        # Le mot de passe est contrôlé avant l'identité : sa réponse ne révèle rien du dossier.
        matricule = attrs['matricule'].strip().upper()
        try:
            validate_password(attrs['password'], User(username=matricule, email=attrs['email']))
        except DjangoValidationError as exc:
            raise ValidationError({'password': list(exc.messages)})
        attrs['matricule'] = matricule
        return attrs


def fiche_pour_matricule(matricule):
    """Fiche étudiant active, sinon fiche enseignant, qui porte ce matricule."""
    return (Etudiant.objects.filter(matricule__iexact=matricule, statut='actif').first()
            or Enseignant.objects.filter(matricule__iexact=matricule).first())


class ActivationView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = [ActivationRateThrottle, LoginIPRateThrottle]

    @transaction.atomic
    def post(self, request):
        serializer = ActivationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        fiche = fiche_pour_matricule(d['matricule'])
        personne = Personne.objects.select_for_update().filter(pk=fiche.pk).first() if fiche else None
        if (personne is None or personne.user_id is not None or personne.est_suspendue
                or (personne.email or '').lower() != d['email'].lower()
                or personne.date_naissance != d['date_naissance']
                or User.objects.filter(username__iexact=fiche.matricule).exists()):
            return Response({'detail': ECHEC_ACTIVATION}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.create_user(username=fiche.matricule, email=personne.email, password=d['password'],
                                        first_name=personne.prenom, last_name=personne.nom)
        personne.user = user
        personne.save()
        journaliser(request, 'core', 'activation_compte', fiche.matricule)
        return Response({'detail': 'Compte activé. Connectez-vous avec votre matricule.',
                         'username': user.username}, status=status.HTTP_201_CREATED)
