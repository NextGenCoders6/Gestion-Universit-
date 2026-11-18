from django.utils import timezone
from rest_framework import serializers

from core.models import Employe
from logistique.models import AffectationTransport, Bus, Trajet


class BusSerializer(serializers.ModelSerializer):
    affectation_active = serializers.SerializerMethodField()

    class Meta:
        model = Bus
        fields = ['id', 'numero', 'plaque', 'capacite', 'statut', 'affectation_active']
        read_only_fields = ['statut']

    def get_affectation_active(self, obj):
        jour = timezone.localdate()
        a = next((x for x in obj.affectations.all() if x.est_active(jour)), None)
        return None if a is None else {'id': a.pk, 'chauffeur': a.chauffeur.personne.nom_complet, 'trajet': a.trajet.nom}


class TrajetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trajet
        fields = ['id', 'nom', 'depart', 'destination', 'heure_depart', 'heure_arrivee']


class AffectationSerializer(serializers.ModelSerializer):
    bus_numero = serializers.CharField(source='bus.numero', read_only=True)
    chauffeur_nom = serializers.CharField(source='chauffeur.personne.nom_complet', read_only=True)
    trajet_nom = serializers.CharField(source='trajet.nom', read_only=True)
    active = serializers.SerializerMethodField()
    chauffeur = serializers.PrimaryKeyRelatedField(queryset=Employe.objects.all())

    class Meta:
        model = AffectationTransport
        fields = ['id', 'bus', 'bus_numero', 'chauffeur', 'chauffeur_nom', 'trajet', 'trajet_nom', 'date_debut',
                  'date_fin', 'active']
        read_only_fields = ['date_fin']

    def get_active(self, obj):
        return obj.est_active(timezone.localdate())
