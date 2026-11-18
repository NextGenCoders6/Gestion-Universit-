"""Règles des affectations : fin, statut du bus, chauffeurs disponibles, alertes."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.models import Employe
from logistique.models import AffectationTransport, Bus


def actives(jour):
    return AffectationTransport.objects.filter(date_debut__lte=jour).filter(
        Q(date_fin__isnull=True) | Q(date_fin__gte=jour))


def terminer(affectation, jour=None):
    affectation.date_fin = jour or timezone.localdate()
    affectation.save()
    return affectation


@transaction.atomic
def changer_statut(bus, statut, jour=None, par=None):
    """Passer un bus hors de l'état actif termine son affectation en cours ce jour-là (décision 3)."""
    if statut not in dict(Bus.STATUTS):
        raise ValidationError({'statut': 'Statut invalide.'})
    jour = jour or timezone.localdate()
    bus = Bus.objects.select_for_update().get(pk=bus.pk)
    terminees = []
    if statut != 'actif':
        for a in actives(jour).filter(bus=bus):
            terminees.append(terminer(a, max(jour, a.date_debut)))
    bus.statut = statut
    bus.save()
    return bus, terminees


def chauffeurs_disponibles(jour=None):
    """Chauffeurs avec un contrat en cours et sans affectation active ce jour-là."""
    from rh.contrats import q_en_cours
    from rh.models import Contrat
    jour = jour or timezone.localdate()
    sous_contrat = Contrat.objects.filter(q_en_cours(jour)).values('personne_id')
    occupes = actives(jour).values('chauffeur_id')
    return (Employe.objects.filter(fonction='chauffeur', pk__in=sous_contrat).exclude(pk__in=occupes)
            .select_related('personne').order_by('personne__nom', 'personne__prenom'))


def alertes(jour=None):
    """Affectations actives dont le chauffeur n'a plus de contrat en cours (décision 4)."""
    from rh.contrats import q_en_cours
    from rh.models import Contrat
    jour = jour or timezone.localdate()
    sous_contrat = set(Contrat.objects.filter(q_en_cours(jour)).values_list('personne_id', flat=True))
    return [{'affectation': a.pk, 'bus': a.bus.numero, 'chauffeur': a.chauffeur.personne.nom_complet,
             'message': f'{a.chauffeur.personne.nom_complet} (bus {a.bus.numero}) n’a plus de contrat en cours : '
                        f'remplacez-le.'}
            for a in actives(jour).select_related('bus', 'chauffeur__personne') if a.chauffeur_id not in sous_contrat]
