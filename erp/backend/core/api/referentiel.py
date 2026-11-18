"""API du référentiel académique (/api/core/…).

Lecture : tout utilisateur connecté (tous les modules s'en servent).
Écriture : responsables Paramètres. Les règles métier sont dans les modèles
(full_clean dans save) ; leurs erreurs remontent en 400 par champ.
"""
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core import models
from core.permissions import LectureAuthentifieeEcritureParametres


class FiltresMixin:
    """`filtres = {'param': 'champ_orm'}` : filtre la liste par paramètres de requête."""

    filtres = {}

    def get_queryset(self):
        qs = super().get_queryset()
        for param, champ in self.filtres.items():
            valeur = self.request.query_params.get(param)
            if valeur not in (None, ''):
                qs = qs.filter(**{champ: valeur})
        return qs


class ReferentielViewSet(FiltresMixin, viewsets.ModelViewSet):
    permission_classes = [LectureAuthentifieeEcritureParametres]


# ── Serializers ──────────────────────────────────────────────────

class AnneeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.AnneeAcademique
        fields = ['id', 'libelle', 'date_debut', 'date_fin', 'statut', 'en_cours']


class PeriodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Periode
        fields = ['id', 'annee', 'numero', 'date_debut', 'date_fin']


class FaculteSerializer(serializers.ModelSerializer):
    titre_doyen = serializers.CharField(read_only=True)
    titre_vice_doyen = serializers.CharField(read_only=True)

    class Meta:
        model = models.Faculte
        fields = ['id', 'nom', 'code', 'logo', 'genre_doyen', 'nom_doyen', 'genre_vice_doyen',
                  'nom_vice_doyen', 'titre_doyen', 'titre_vice_doyen']


class DepartementSerializer(serializers.ModelSerializer):
    faculte_code = serializers.CharField(source='faculte.code', read_only=True)
    chef_nom = serializers.CharField(source='chef.personne.nom_complet', read_only=True, default=None)

    class Meta:
        model = models.Departement
        fields = ['id', 'libelle', 'faculte', 'faculte_code', 'chef', 'chef_nom']


class PortailSerializer(serializers.ModelSerializer):
    faculte_code = serializers.CharField(source='faculte.code', read_only=True)

    class Meta:
        model = models.Portail
        fields = ['id', 'nom', 'code', 'faculte', 'faculte_code']


class FiliereSerializer(serializers.ModelSerializer):
    departement_libelle = serializers.CharField(source='departement.libelle', read_only=True)
    portail_code = serializers.CharField(source='portail.code', read_only=True)
    faculte_code = serializers.CharField(source='departement.faculte.code', read_only=True)
    responsable_nom = serializers.CharField(source='responsable.personne.nom_complet', read_only=True, default=None)

    class Meta:
        model = models.Filiere
        fields = ['id', 'nom', 'code', 'departement', 'departement_libelle', 'portail', 'portail_code',
                  'faculte_code', 'responsable', 'responsable_nom']


class ParcoursSerializer(serializers.ModelSerializer):
    code = serializers.CharField(read_only=True)
    semestres = serializers.ListField(read_only=True)

    class Meta:
        model = models.Parcours
        fields = ['id', 'type_parcours', 'niveau', 'code', 'semestres']


class ClasseSerializer(serializers.ModelSerializer):
    parcours_code = serializers.CharField(source='parcours.code', read_only=True)
    annee_libelle = serializers.CharField(source='annee.libelle', read_only=True)
    semestres = serializers.ListField(read_only=True)

    class Meta:
        model = models.Classe
        fields = ['id', 'libelle', 'annee', 'annee_libelle', 'parcours', 'parcours_code', 'portail',
                  'filiere', 'semestres']
        read_only_fields = ['libelle']
        validators = []  # unicité contrôlée par Classe.clean (message français)


class UESerializer(serializers.ModelSerializer):
    credits_total = serializers.IntegerField(read_only=True)
    rattachement = serializers.SerializerMethodField()

    class Meta:
        model = models.UniteEnseignement
        fields = ['id', 'code', 'libelle', 'semestre', 'portail', 'filiere', 'rattachement', 'credits_total']

    def get_rattachement(self, obj):
        return obj.portail.code if obj.portail_id else obj.filiere.code


class ECSerializer(serializers.ModelSerializer):
    ue_code = serializers.CharField(source='ue.code', read_only=True)
    semestre = serializers.CharField(source='ue.semestre', read_only=True)
    departement_libelle = serializers.CharField(source='departement.libelle', read_only=True)
    heures_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = models.ElementConstitutif
        fields = ['id', 'code', 'libelle', 'ue', 'ue_code', 'semestre', 'credits', 'heures_cm', 'heures_td',
                  'heures_tp', 'heures_total', 'departement', 'departement_libelle', 'description']


# ── ViewSets ─────────────────────────────────────────────────────

class AnneeViewSet(ReferentielViewSet):
    queryset = models.AnneeAcademique.objects.all()
    serializer_class = AnneeSerializer
    filtres = {'statut': 'statut'}

    @action(detail=True, methods=['post'])
    def definir_en_cours(self, request, pk=None):
        annee = self.get_object()
        annee.en_cours = True
        annee.save()
        return Response(self.get_serializer(annee).data)


class PeriodeViewSet(ReferentielViewSet):
    queryset = models.Periode.objects.select_related('annee')
    serializer_class = PeriodeSerializer
    filtres = {'annee': 'annee_id'}


class FaculteViewSet(ReferentielViewSet):
    queryset = models.Faculte.objects.all()
    serializer_class = FaculteSerializer


class DepartementViewSet(ReferentielViewSet):
    queryset = models.Departement.objects.select_related('faculte', 'chef__personne')
    serializer_class = DepartementSerializer
    filtres = {'faculte': 'faculte_id'}


class PortailViewSet(ReferentielViewSet):
    queryset = models.Portail.objects.select_related('faculte')
    serializer_class = PortailSerializer
    filtres = {'faculte': 'faculte_id'}


class FiliereViewSet(ReferentielViewSet):
    queryset = models.Filiere.objects.select_related('departement__faculte', 'portail', 'responsable__personne')
    serializer_class = FiliereSerializer
    filtres = {'departement': 'departement_id', 'portail': 'portail_id', 'faculte': 'departement__faculte_id'}


class ParcoursViewSet(ReferentielViewSet):
    queryset = models.Parcours.objects.all()
    serializer_class = ParcoursSerializer


class ClasseViewSet(ReferentielViewSet):
    queryset = models.Classe.objects.select_related('annee', 'parcours', 'portail__faculte', 'filiere__departement')
    serializer_class = ClasseSerializer
    filtres = {'annee': 'annee_id', 'parcours': 'parcours_id'}

    def get_queryset(self):
        qs = super().get_queryset()
        faculte = self.request.query_params.get('faculte')
        if faculte:
            from django.db.models import Q
            qs = qs.filter(Q(portail__faculte_id=faculte) | Q(filiere__departement__faculte_id=faculte))
        return qs


class UEViewSet(ReferentielViewSet):
    queryset = models.UniteEnseignement.objects.select_related('portail', 'filiere').prefetch_related('ecs')
    serializer_class = UESerializer
    filtres = {'semestre': 'semestre', 'portail': 'portail_id', 'filiere': 'filiere_id'}


class ECViewSet(ReferentielViewSet):
    queryset = models.ElementConstitutif.objects.select_related('ue', 'departement')
    serializer_class = ECSerializer
    filtres = {'ue': 'ue_id', 'departement': 'departement_id', 'semestre': 'ue__semestre'}
