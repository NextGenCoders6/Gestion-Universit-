from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from core.models import Departement, Employe, Enseignant, Faculte, Personne
from rh.contrats import contrat_en_cours
from rh.models import Contrat
from rh.permissions import voit_donnees_sensibles


def masquer(valeur):
    valeur = (valeur or '').strip()
    return f'•••• {valeur[-4:]}' if valeur else ''


class PersonneRHSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(read_only=True)

    class Meta:
        model = Personne
        fields = ['id', 'nom', 'prenom', 'nom_complet', 'genre', 'date_naissance', 'lieu_naissance', 'nationalite',
                  'email', 'telephone', 'adresse', 'photo', 'statut']
        read_only_fields = ['id', 'photo', 'statut']
        extra_kwargs = {'email': {'required': False, 'allow_null': True, 'allow_blank': True}}

    def validate_email(self, valeur):
        return valeur or None


class ContratSerializer(serializers.ModelSerializer):
    etat = serializers.SerializerMethodField()
    personne_nom = serializers.CharField(source='personne.nom_complet', read_only=True)
    role = serializers.SerializerMethodField()

    class Meta:
        model = Contrat
        fields = ['id', 'personne', 'personne_nom', 'role', 'type', 'date_debut', 'date_fin', 'salaire_mensuel',
                  'taux_horaire', 'rib', 'numero_secu', 'diplome', 'etat']

    def get_etat(self, obj):
        return obj.etat()

    def validate(self, attrs):
        c = self.instance
        if c is not None:
            if 'personne' in attrs and attrs['personne'] != c.personne:
                raise serializers.ValidationError({'personne': 'Un contrat ne change pas de titulaire : créez-en un nouveau.'})
            utilise = c.vacations.exists() or (hasattr(c, 'paies') and c.paies.exists())
            if utilise and 'type' in attrs and attrs['type'] != c.type:
                raise serializers.ValidationError({'type': 'Ce contrat a déjà des vacations ou de la paie : son type ne change plus.'})
        return attrs

    def get_role(self, obj):
        return 'enseignant' if hasattr(obj.personne, 'enseignant') else 'employe'

    def to_representation(self, obj):
        donnees = super().to_representation(obj)
        request = self.context.get('request')
        if request is None or not voit_donnees_sensibles(request.user):
            donnees['rib'] = masquer(donnees['rib'])
            donnees['numero_secu'] = masquer(donnees['numero_secu'])
        return donnees


class ContratImbriqueSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contrat
        fields = ['type', 'date_debut', 'date_fin', 'salaire_mensuel', 'taux_horaire', 'rib', 'numero_secu', 'diplome']


def contrat_resume(personne):
    c = contrat_en_cours(personne)
    return None if c is None else {'id': c.pk, 'type': c.type, 'date_debut': c.date_debut, 'date_fin': c.date_fin}


class FicheRHMixin(serializers.Serializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    matricule = serializers.CharField(read_only=True)
    nom_complet = serializers.CharField(source='personne.nom_complet', read_only=True)
    contrat_en_cours = serializers.SerializerMethodField()
    actif = serializers.SerializerMethodField()

    def _contrat(self, obj):
        # Contrats en cours préchargés par la vue (dict personne_id → contrat) : pas de requête par ligne.
        cache = self.context.get('contrats_en_cours')
        if cache is not None:
            c = cache.get(obj.pk)
            return None if c is None else {'id': c.pk, 'type': c.type, 'date_debut': c.date_debut, 'date_fin': c.date_fin}
        return contrat_resume(obj.personne)

    def get_contrat_en_cours(self, obj):
        return self._contrat(obj)

    def get_actif(self, obj):
        return self._contrat(obj) is not None


class CreationAvecContratMixin:
    """Crée la personne, le rôle et, s'il est fourni, le premier contrat, en une transaction."""

    role_model = None
    champs_role = ()

    @transaction.atomic
    def create(self, donnees):
        personne = Personne.objects.create(**donnees.pop('personne'))
        contrat = donnees.pop('contrat', None)
        role = self.role_model.objects.create(personne=personne, **{c: donnees[c] for c in self.champs_role if c in donnees})
        if contrat:
            try:
                Contrat.objects.create(personne=personne, **contrat)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'contrat': exc.message_dict})
        return role

    def update(self, instance, donnees):
        donnees.pop('personne', None)
        donnees.pop('contrat', None)
        for champ in self.champs_role:
            if champ in donnees:
                setattr(instance, champ, donnees[champ])
        instance.save()
        return instance


class EnseignantRHSerializer(CreationAvecContratMixin, FicheRHMixin, serializers.ModelSerializer):
    personne = PersonneRHSerializer()
    contrat = ContratImbriqueSerializer(write_only=True, required=False)
    departement_libelle = serializers.CharField(source='departement.libelle', read_only=True)
    faculte = serializers.CharField(source='departement.faculte.code', read_only=True)
    est_chef = serializers.SerializerMethodField()
    departement = serializers.PrimaryKeyRelatedField(queryset=Departement.objects.all())
    role_model = Enseignant
    champs_role = ('departement', 'grade')

    class Meta:
        model = Enseignant
        fields = ['id', 'matricule', 'nom_complet', 'personne', 'departement', 'departement_libelle', 'faculte', 'grade',
                  'est_chef', 'contrat', 'contrat_en_cours', 'actif']

    def get_est_chef(self, obj):
        return obj.departement.chef_id == obj.pk


class EmployeRHSerializer(CreationAvecContratMixin, FicheRHMixin, serializers.ModelSerializer):
    personne = PersonneRHSerializer()
    contrat = ContratImbriqueSerializer(write_only=True, required=False)
    fonction_libelle = serializers.SerializerMethodField()
    faculte_rattachement = serializers.PrimaryKeyRelatedField(queryset=Faculte.objects.all(), required=False,
                                                              allow_null=True)
    role_model = Employe
    champs_role = ('fonction', 'fonction_autre', 'lieu_travail', 'faculte_rattachement')

    class Meta:
        model = Employe
        fields = ['id', 'matricule', 'nom_complet', 'personne', 'fonction', 'fonction_autre', 'fonction_libelle',
                  'lieu_travail', 'faculte_rattachement', 'contrat', 'contrat_en_cours', 'actif']

    def get_fonction_libelle(self, obj):
        return obj.fonction_autre if obj.fonction == 'autre' and obj.fonction_autre else obj.get_fonction_display()

    def validate(self, attrs):
        fonction = attrs.get('fonction', getattr(self.instance, 'fonction', None))
        autre = attrs.get('fonction_autre', getattr(self.instance, 'fonction_autre', ''))
        if fonction == 'autre' and not (autre or '').strip():
            raise serializers.ValidationError({'fonction_autre': "Précisez la fonction (« Autre »)."})
        return attrs
