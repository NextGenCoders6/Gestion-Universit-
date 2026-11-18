from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.response import Response

from core.audit import journaliser
from core.droits import a_droit, modules_accessibles
from core.models import Personne

ROLES = ('etudiant', 'enseignant', 'employe')


class SuppressionImpossible(APIException):
    status_code = 400
    default_code = 'suppression_impossible'


class PersonnesPermission(BasePermission):
    """Lecture : tout utilisateur ayant au moins un module. Écriture : Paramètres."""

    message = 'Accès non autorisé.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return bool(modules_accessibles(user))
        return a_droit(user, 'parametres')


class PersonneSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()
    username = serializers.CharField(source='user.username', read_only=True, default=None)

    class Meta:
        model = Personne
        fields = ['id', 'nom', 'prenom', 'nom_complet', 'genre', 'date_naissance', 'lieu_naissance', 'nationalite',
                  'email', 'telephone', 'adresse', 'photo', 'statut', 'motif_suspension', 'username', 'roles']
        read_only_fields = ['statut', 'motif_suspension']
        extra_kwargs = {'email': {'required': False, 'allow_null': True, 'allow_blank': True}}

    def get_roles(self, obj):
        return [r for r in ROLES if hasattr(obj, r)]

    def validate_email(self, valeur):
        return valeur or None


class PersonneViewSet(viewsets.ModelViewSet):
    serializer_class = PersonneSerializer
    permission_classes = [PersonnesPermission]

    def get_queryset(self):
        qs = Personne.objects.select_related('user', 'etudiant', 'enseignant', 'employe')
        q = self.request.query_params.get('q', '').strip()
        if q:
            qs = qs.filter(Q(nom__icontains=q) | Q(prenom__icontains=q) | Q(email__icontains=q))
        role = self.request.query_params.get('role')
        if role in ROLES:
            qs = qs.filter(**{f'{role}__isnull': False})
        return qs

    def perform_destroy(self, personne):
        # Supprimer la fiche effacerait en cascade ses rôles (matricule, département…).
        utilisations = [libelle for role, libelle in (('etudiant', 'un dossier étudiant'),
                        ('enseignant', 'une fiche enseignant'), ('employe', 'une fiche employé'))
                        if hasattr(personne, role)]
        if personne.user_id:
            utilisations.append('un compte utilisateur')
        if utilisations:
            raise SuppressionImpossible(
                f'Suppression impossible : la personne est encore utilisée par {", ".join(utilisations)}.'
            )
        description = str(personne)
        personne.delete()
        journaliser(self.request, 'parametres', 'suppression_personne', description)

    @action(detail=True, methods=['post'])
    def suspendre(self, request, pk=None):
        personne = self.get_object()
        motif = (request.data.get('motif') or '').strip()
        if not motif:
            raise ValidationError({'motif': 'Le motif de suspension est obligatoire.'})
        personne.statut, personne.motif_suspension = 'suspendu', motif
        personne.save()
        journaliser(request, 'parametres', 'suspension', f'{personne} — {motif}')
        return Response(self.get_serializer(personne).data)

    @action(detail=True, methods=['post'])
    def reactiver(self, request, pk=None):
        personne = self.get_object()
        personne.statut = 'actif'
        personne.save()
        journaliser(request, 'parametres', 'reactivation', str(personne))
        return Response(self.get_serializer(personne).data)
