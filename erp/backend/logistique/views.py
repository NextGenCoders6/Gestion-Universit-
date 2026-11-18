"""API de la Logistique : tableau de bord, bus, trajets, affectations, chauffeurs, coûts."""
from datetime import date

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.filtres import entier
from core.audit import journaliser
from logistique import affectations as service
from logistique.models import AffectationTransport, Bus, Trajet
from logistique.permissions import LectureLogistique
from logistique.serializers import AffectationSerializer, BusSerializer, TrajetSerializer


def _date(valeur, champ):
    if valeur in (None, ''):
        return None
    try:
        return date.fromisoformat(str(valeur))
    except ValueError:
        raise ValidationError({champ: 'Date invalide (AAAA-MM-JJ attendu).'})


class BusViewSet(viewsets.ModelViewSet):
    permission_classes = [LectureLogistique]
    serializer_class = BusSerializer
    queryset = Bus.objects.prefetch_related('affectations__chauffeur__personne', 'affectations__trajet')

    def perform_create(self, serializer):
        journaliser(self.request, 'logistique', 'bus', f'Création : {serializer.save()}')

    def perform_update(self, serializer):
        journaliser(self.request, 'logistique', 'bus', f'Modification : {serializer.save()}')

    def perform_destroy(self, instance):
        description = str(instance)
        instance.delete()
        journaliser(self.request, 'logistique', 'bus', f'Suppression : {description}')

    @action(detail=True, methods=['post'])
    def statut(self, request, pk=None):
        bus, terminees = service.changer_statut(self.get_object(), request.data.get('statut'), par=request.user)
        journaliser(request, 'logistique', 'statut_bus', f'{bus} → {bus.statut} ({len(terminees)} affectation(s) terminée(s))')
        donnees = BusSerializer(self.get_queryset().get(pk=bus.pk)).data
        return Response({**donnees, 'affectations_terminees': len(terminees)})


class TrajetViewSet(viewsets.ModelViewSet):
    permission_classes = [LectureLogistique]
    serializer_class = TrajetSerializer
    queryset = Trajet.objects.all()

    def perform_destroy(self, instance):
        description = str(instance)
        instance.delete()
        journaliser(self.request, 'logistique', 'trajet', f'Suppression : {description}')


class AffectationViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin,
                         viewsets.GenericViewSet):
    permission_classes = [LectureLogistique]
    serializer_class = AffectationSerializer

    def get_queryset(self):
        qs = AffectationTransport.objects.select_related('bus', 'chauffeur__personne', 'trajet')
        if self.request.query_params.get('actives') == 'true':
            qs = qs.filter(pk__in=service.actives(timezone.localdate()).values('pk'))
        bus = entier(self.request, 'bus')
        return qs.filter(bus_id=bus) if bus is not None else qs

    def perform_create(self, serializer):
        a = serializer.save()
        journaliser(self.request, 'logistique', 'affectation', f'{a} à partir du {a.date_debut:%d/%m/%Y}')

    @action(detail=True, methods=['post'])
    def terminer(self, request, pk=None):
        a = service.terminer(self.get_object(), _date(request.data.get('date_fin'), 'date_fin'))
        journaliser(request, 'logistique', 'fin_affectation', f'{a} au {a.date_fin:%d/%m/%Y}')
        return Response(AffectationSerializer(a).data)


class ChauffeursView(APIView):
    permission_classes = [LectureLogistique]

    def get(self, request):
        jour = _date(request.query_params.get('date'), 'date') or timezone.localdate()
        return Response([{'id': e.pk, 'matricule': e.matricule, 'nom_complet': e.personne.nom_complet,
                          'telephone': e.personne.telephone} for e in service.chauffeurs_disponibles(jour)])


def _f(v):
    return float(v)


def couts_json(c):
    return {'total': _f(c['total']), 'par_type': {k: _f(v) for k, v in c['par_type'].items()},
            'par_mois': {k: _f(v) for k, v in c['par_mois'].items()},
            'par_bus': [{**l, 'total': _f(l['total'])} for l in c['par_bus']]}


class CoutsView(APIView):
    """Lecture des dépenses de transport enregistrées par la Finance."""

    permission_classes = [LectureLogistique]

    def get(self, request):
        from finance.transports import couts
        bus_id = entier(request, 'bus')
        bus = get_object_or_404(Bus, pk=bus_id) if bus_id is not None else None
        return Response(couts_json(couts(bus=bus, debut=_date(request.query_params.get('debut'), 'debut'),
                                         fin=_date(request.query_params.get('fin'), 'fin'))))


class TableauDeBordView(APIView):
    permission_classes = [LectureLogistique]

    def get(self, request):
        from finance.transports import couts
        jour = timezone.localdate()
        statuts = dict(Bus.objects.values_list('statut').annotate(n=Count('pk')))
        annee_debut = date(jour.year if jour.month >= 9 else jour.year - 1, 9, 1)
        return Response({
            'bus_par_statut': {s: statuts.get(s, 0) for s, _ in Bus.STATUTS},
            'affectations_actives': service.actives(jour).count(),
            'chauffeurs_disponibles': service.chauffeurs_disponibles(jour).count(),
            'alertes': service.alertes(jour),
            'couts_mois': _f(couts(debut=jour.replace(day=1), fin=jour)['total']),
            'couts_annee': _f(couts(debut=annee_debut, fin=jour)['total']),
        })
