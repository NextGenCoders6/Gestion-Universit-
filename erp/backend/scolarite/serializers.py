from django.db import transaction
from django.db.models import Q
from rest_framework import serializers

from core.models import Classe, Etudiant, Personne
from scolarite.inscriptions import inscrire
from scolarite.models import Inscription
from scolarite.perimetre import restreindre_par_faculte


def classes_du_perimetre(user):
    qs = Classe.objects.select_related('annee', 'parcours', 'portail', 'filiere')
    return restreindre_par_faculte(qs, user)


class InscriptionSerializer(serializers.ModelSerializer):
    classe_libelle = serializers.CharField(source='classe.libelle', read_only=True)
    annee_libelle = serializers.CharField(source='annee.libelle', read_only=True)
    niveau = serializers.CharField(source='classe.parcours.code', read_only=True)
    matricule = serializers.CharField(source='etudiant.matricule', read_only=True)
    nom_complet = serializers.CharField(source='etudiant.personne.nom_complet', read_only=True)

    class Meta:
        model = Inscription
        fields = ['id', 'etudiant', 'matricule', 'nom_complet', 'classe', 'classe_libelle', 'annee', 'annee_libelle',
                  'niveau', 'type', 'statut', 'date_inscription']
        read_only_fields = ['annee', 'statut']
        extra_kwargs = {'date_inscription': {'required': False}, 'type': {'required': False}}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request is not None:
            self.fields['classe'].queryset = classes_du_perimetre(request.user)
            # Étudiants du périmètre, ou sans aucune inscription.
            visibles = restreindre_par_faculte(Etudiant.objects.all(), request.user, prefixe='inscriptions__classe__')
            self.fields['etudiant'].queryset = Etudiant.objects.filter(
                Q(pk__in=visibles.values('pk')) | Q(inscriptions__isnull=True)).distinct()
        if self.instance is not None:
            # Une inscription existante ne change que de classe.
            self.fields['etudiant'].read_only = True
            self.fields['type'].read_only = True

    def create(self, donnees):
        return inscrire(donnees['etudiant'], donnees['classe'], type=donnees.get('type', 'reinscription'),
                        date=donnees.get('date_inscription'))


class InscriptionCouranteSerializer(serializers.ModelSerializer):
    classe_libelle = serializers.CharField(source='classe.libelle', read_only=True)

    class Meta:
        model = Inscription
        fields = ['id', 'classe', 'classe_libelle', 'annee', 'statut']


class EtudiantListeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    nom = serializers.CharField(source='personne.nom', read_only=True)
    prenom = serializers.CharField(source='personne.prenom', read_only=True)
    nom_complet = serializers.CharField(source='personne.nom_complet', read_only=True)
    genre = serializers.CharField(source='personne.genre', read_only=True)
    email = serializers.EmailField(source='personne.email', read_only=True)
    photo = serializers.ImageField(source='personne.photo', read_only=True)
    a_un_compte = serializers.SerializerMethodField()
    inscription_courante = serializers.SerializerMethodField()

    class Meta:
        model = Etudiant
        fields = ['id', 'matricule', 'nom', 'prenom', 'nom_complet', 'genre', 'email', 'photo', 'statut',
                  'a_un_compte', 'inscription_courante']

    def get_a_un_compte(self, obj):
        return obj.personne.user_id is not None

    def get_inscription_courante(self, obj):
        # Les inscriptions sont préchargées, la plus récente en premier.
        inscriptions = list(obj.inscriptions.all())
        return InscriptionCouranteSerializer(inscriptions[0]).data if inscriptions else None


class PersonneEtudiantSerializer(serializers.ModelSerializer):
    """Identité saisie par le secrétariat : e-mail et date de naissance servent à activer le compte."""

    nom_complet = serializers.CharField(read_only=True)

    class Meta:
        model = Personne
        fields = ['id', 'nom', 'prenom', 'nom_complet', 'genre', 'date_naissance', 'lieu_naissance', 'nationalite',
                  'email', 'telephone', 'adresse', 'photo', 'statut']
        read_only_fields = ['id', 'photo', 'statut']
        extra_kwargs = {
            'email': {'required': True, 'allow_null': False, 'allow_blank': False},
            'date_naissance': {'required': True, 'allow_null': False},
        }


class EtudiantFicheSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    personne = PersonneEtudiantSerializer(read_only=True)
    inscriptions = InscriptionSerializer(many=True, read_only=True)
    a_un_compte = serializers.SerializerMethodField()

    class Meta:
        model = Etudiant
        fields = ['id', 'matricule', 'statut', 'annee_entree', 'personne', 'a_un_compte', 'inscriptions']

    def get_a_un_compte(self, obj):
        return obj.personne.user_id is not None


class EtudiantCreationSerializer(serializers.Serializer):
    """Crée en un appel la personne, le dossier étudiant (matricule) et sa première inscription."""

    personne = PersonneEtudiantSerializer()
    classe = serializers.PrimaryKeyRelatedField(queryset=Classe.objects.none())
    date_inscription = serializers.DateField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request is not None:
            self.fields['classe'].queryset = classes_du_perimetre(request.user)

    @transaction.atomic
    def create(self, donnees):
        classe = donnees['classe']
        personne = Personne.objects.create(**donnees['personne'])
        etudiant = Etudiant.objects.create(personne=personne, annee_entree=classe.annee)
        inscrire(etudiant, classe, type='premiere', date=donnees.get('date_inscription'))
        return etudiant


class StatutSerializer(serializers.Serializer):
    statut = serializers.ChoiceField(choices=Etudiant.STATUT_CHOICES)
