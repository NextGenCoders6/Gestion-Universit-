from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.audit import journaliser
from core.droits import MODULES, definir_droits, tous_les_groupes
from core.models import Faculte, JournalAudit, Personne
from core.models.acces import RattachementFaculte
from core.permissions import droit_module

User = get_user_model()
DroitParametres = droit_module('parametres')


def _valider_mot_de_passe(valeur, user=None):
    try:
        validate_password(valeur, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages))
    return valeur


class UtilisateurSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    groupes = serializers.ListField(child=serializers.CharField(), required=False)
    personne_id = serializers.PrimaryKeyRelatedField(
        queryset=Personne.objects.all(), required=False, allow_null=True, write_only=True
    )
    faculte_rattachee_id = serializers.PrimaryKeyRelatedField(
        queryset=Faculte.objects.all(), required=False, allow_null=True, write_only=True
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'is_active', 'password', 'groupes', 'personne_id', 'faculte_rattachee_id']

    def validate_groupes(self, valeur):
        inconnus = [g for g in valeur if g not in tous_les_groupes()]
        if inconnus:
            raise serializers.ValidationError(f'Groupe(s) inconnu(s) : {", ".join(inconnus)}')
        return valeur

    def validate_password(self, valeur):
        return _valider_mot_de_passe(valeur, self.instance)

    def validate(self, attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'Le mot de passe est obligatoire.'})
        return attrs

    def to_representation(self, user):
        data = super().to_representation(user)
        connus = set(tous_les_groupes())
        data['groupes'] = sorted(g for g in user.groups.values_list('name', flat=True) if g in connus)
        personne = getattr(user, 'personne', None)
        data['personne_id'] = personne.pk if personne else None
        data['nom_complet'] = personne.nom_complet if personne else user.username
        rattachement = getattr(user, 'rattachement_faculte', None)
        data['faculte_rattachee_id'] = rattachement.faculte_id if rattachement else None
        return data

    def _appliquer(self, user, attrs):
        if 'groupes' in attrs:
            definir_droits(user, attrs['groupes'])
        if 'personne_id' in attrs:
            Personne.objects.filter(user=user).exclude(pk=getattr(attrs['personne_id'], 'pk', None)).update(user=None)
            if attrs['personne_id'] is not None:
                p = attrs['personne_id']
                p.user = user
                p.save()
        if 'faculte_rattachee_id' in attrs:
            RattachementFaculte.objects.filter(user=user).delete()
            if attrs['faculte_rattachee_id'] is not None:
                RattachementFaculte.objects.create(user=user, faculte=attrs['faculte_rattachee_id'])
        # Les relations inverses ont pu être mises en cache avant la modification.
        user._state.fields_cache.pop('rattachement_faculte', None)
        user._state.fields_cache.pop('personne', None)

    @transaction.atomic
    def create(self, attrs):
        user = User.objects.create_user(username=attrs['username'], password=attrs['password'],
                                        is_active=attrs.get('is_active', True))
        self._appliquer(user, attrs)
        return user

    @transaction.atomic
    def update(self, user, attrs):
        for champ in ('username', 'is_active'):
            if champ in attrs:
                setattr(user, champ, attrs[champ])
        if attrs.get('password'):
            user.set_password(attrs['password'])
        user.save()
        self._appliquer(user, attrs)
        return user


class UtilisateurViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                         mixins.UpdateModelMixin, viewsets.GenericViewSet):
    serializer_class = UtilisateurSerializer
    permission_classes = [DroitParametres]

    def get_queryset(self):
        qs = User.objects.select_related('personne', 'rattachement_faculte').prefetch_related('groups').order_by('username')
        q = self.request.query_params.get('q', '').strip()
        return qs.filter(username__icontains=q) if q else qs

    def perform_create(self, serializer):
        user = serializer.save()
        journaliser(self.request, 'parametres', 'creation_utilisateur',
                    f'{user.username} — droits : {", ".join(serializer.validated_data.get("groupes", [])) or "aucun"}')

    def perform_update(self, serializer):
        user = serializer.save()
        if 'groupes' in serializer.validated_data or 'faculte_rattachee_id' in serializer.validated_data:
            journaliser(self.request, 'parametres', 'modification_droits',
                        f'{user.username} — droits : {", ".join(serializer.validated_data.get("groupes", [])) or "inchangés"}')
        else:
            journaliser(self.request, 'parametres', 'modification_utilisateur', user.username)

    @action(detail=True, methods=['post'])
    def mot_de_passe(self, request, pk=None):
        user = self.get_object()
        valeur = request.data.get('password') or ''
        try:
            _valider_mot_de_passe(valeur, user)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({'password': exc.detail})
        user.set_password(valeur)
        user.save()
        journaliser(request, 'parametres', 'mot_de_passe', user.username)
        return Response({'detail': 'Mot de passe modifié.'})


class ModulesView(APIView):
    def get(self, request):
        return Response([{'code': c, 'libelle': m['libelle'], 'niveaux': m['niveaux']} for c, m in MODULES.items()])


class AuditSerializer(serializers.ModelSerializer):
    utilisateur = serializers.CharField(source='utilisateur.username', read_only=True, default=None)

    class Meta:
        model = JournalAudit
        fields = ['id', 'date', 'utilisateur', 'module', 'action', 'description', 'adresse_ip']


class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditSerializer
    permission_classes = [DroitParametres]

    def get_queryset(self):
        qs = JournalAudit.objects.select_related('utilisateur')
        module = self.request.query_params.get('module')
        if module:
            qs = qs.filter(module=module)
        utilisateur = self.request.query_params.get('utilisateur')
        if utilisateur:
            qs = qs.filter(utilisateur_id=utilisateur)
        return qs
