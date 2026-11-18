from rest_framework import serializers

from core.models import Enseignant
from edt import quotas
from edt.models import AffectationEC, DocumentPedagogique, ReferentClasse, Seance


class SeanceSerializer(serializers.ModelSerializer):
    ec_code = serializers.CharField(source='ec.code', read_only=True)
    ec_libelle = serializers.CharField(source='ec.libelle', read_only=True)
    classe_libelle = serializers.CharField(source='classe.libelle', read_only=True)
    enseignant_nom = serializers.CharField(source='enseignant.personne.nom_complet', read_only=True)
    annee = serializers.IntegerField(source='classe.annee_id', read_only=True)
    creneau_effectif = serializers.SerializerMethodField()

    class Meta:
        model = Seance
        fields = ['id', 'libelle', 'date_seance', 'heure_debut', 'heure_fin', 'type_seance', 'statut',
                  'date_report', 'heure_debut_report', 'heure_fin_report', 'ec', 'ec_code', 'ec_libelle',
                  'classe', 'classe_libelle', 'enseignant', 'enseignant_nom', 'annee', 'seance_liee',
                  'creneau_effectif']
        read_only_fields = ['date_report', 'heure_debut_report', 'heure_fin_report']

    def get_creneau_effectif(self, obj):
        jour, debut, fin = obj.creneau_effectif()
        return {'jour': jour.isoformat() if jour else None,
                'debut': debut.strftime('%H:%M') if debut else None,
                'fin': fin.strftime('%H:%M') if fin else None}

    def validate_statut(self, valeur):
        """Création en brouillon ; publication et report passent par leurs actions."""
        actuel = self.instance.statut if self.instance else None
        if valeur == actuel or (self.instance is None and valeur == 'brouillon'):
            return valeur
        if self.instance is not None and valeur in ('brouillon', 'Annulée') and actuel != 'Reportée':
            return valeur
        raise serializers.ValidationError(
            'Utilisez « Publier » pour confirmer une séance et « Reporter » pour la reporter.'
        )


class ReportSerializer(serializers.Serializer):
    date_report = serializers.DateField()
    heure_debut_report = serializers.TimeField()
    heure_fin_report = serializers.TimeField()


class AffectationSerializer(serializers.ModelSerializer):
    ec_code = serializers.CharField(source='ec.code', read_only=True)
    ec_libelle = serializers.CharField(source='ec.libelle', read_only=True)
    classe_libelle = serializers.CharField(source='classe.libelle', read_only=True)
    enseignant_nom = serializers.CharField(source='enseignant.personne.nom_complet', read_only=True)
    heures_consommees = serializers.SerializerMethodField()
    heures_effectuees = serializers.SerializerMethodField()
    heures_restantes = serializers.SerializerMethodField()
    warnings = serializers.SerializerMethodField()

    class Meta:
        model = AffectationEC
        fields = ['id', 'ec', 'ec_code', 'ec_libelle', 'classe', 'classe_libelle', 'enseignant', 'enseignant_nom',
                  'type_seance', 'heures_prevues', 'hors_departement', 'heures_consommees', 'heures_effectuees',
                  'heures_restantes', 'warnings']

    def get_heures_consommees(self, obj):
        return obj.heures_consommees()

    def get_heures_effectuees(self, obj):
        return obj.heures_effectuees()

    def get_heures_restantes(self, obj):
        return obj.heures_restantes()

    def get_warnings(self, obj):
        if obj.has_volume_warning():
            return [f'Le total des affectations ({obj.volume_total_affectations():g} h) dépasse le volume de '
                    f"l'EC {obj.ec.code} ({quotas.heures_max(obj.ec)} h)."]
        return []


class ReferentSerializer(serializers.ModelSerializer):
    enseignant_nom = serializers.CharField(source='enseignant.personne.nom_complet', read_only=True)
    classes_libelles = serializers.SerializerMethodField()

    class Meta:
        model = ReferentClasse
        fields = ['id', 'enseignant', 'enseignant_nom', 'classes', 'classes_libelles']

    def get_classes_libelles(self, obj):
        return [c.libelle for c in obj.classes.all()]


class EnseignantSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', read_only=True)
    nom_complet = serializers.CharField(source='personne.nom_complet', read_only=True)
    departement_libelle = serializers.CharField(source='departement.libelle', read_only=True)

    class Meta:
        model = Enseignant
        fields = ['id', 'matricule', 'nom_complet', 'grade', 'departement', 'departement_libelle']


class DocumentSerializer(serializers.ModelSerializer):
    ec_code = serializers.CharField(source='ec.code', read_only=True)
    classe_libelle = serializers.CharField(source='classe.libelle', read_only=True)
    enseignant_nom = serializers.CharField(source='enseignant.personne.nom_complet', read_only=True)
    nom_fichier = serializers.SerializerMethodField()

    class Meta:
        model = DocumentPedagogique
        fields = ['id', 'titre', 'fichier', 'nom_fichier', 'type_doc', 'ec', 'ec_code', 'classe', 'classe_libelle',
                  'enseignant', 'enseignant_nom', 'created_at']
        extra_kwargs = {'fichier': {'write_only': True}}

    def get_fields(self):
        champs = super().get_fields()
        if self.context.get('enseignant_impose'):  # dépôt depuis Mon espace : c'est l'enseignant connecté
            champs['enseignant'].read_only = True
        return champs

    def get_nom_fichier(self, obj):
        import os
        return os.path.basename(obj.fichier.name) if obj.fichier else None
