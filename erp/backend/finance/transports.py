"""Dépenses de transport : saisie (journal), annulation, coûts lus par la Logistique."""
from collections import defaultdict
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from finance import journal
from finance.models import DepenseTransport


@transaction.atomic
def enregistrer(bus, type, montant, *, date=None, description='', par=None, historique=False):
    montant = journal.montant_valide(montant)
    if type not in dict(DepenseTransport.TYPES):
        raise ValidationError({'type': 'Type de dépense invalide.'})
    jour = journal.date_valide(date, historique=historique)
    libelle = f'Transport — {dict(DepenseTransport.TYPES)[type]} — {bus}'
    if description:
        libelle += f' ({description})'
    operation = journal.ecrire(libelle, -montant, 'transport', jour, par)
    return DepenseTransport.objects.create(bus=bus, type=type, montant=montant, description=(description or '')[:255],
                                           date=jour, operation=operation, par=par)


@transaction.atomic
def annuler_depense(depense, motif, par=None):
    motif = (motif or '').strip()
    if not motif:
        raise ValidationError({'motif': "Indiquez le motif de l'annulation."})
    depense = DepenseTransport.objects.select_for_update().select_related('operation').get(pk=depense.pk)
    if depense.annule:
        raise ValidationError('Cette dépense est déjà annulée.')
    contre = journal.ecrire(f'Annulation — {depense.operation.libelle} ({motif})', depense.montant, 'annulation',
                            timezone.localdate(), par, annule=depense.operation)
    depense.annule = True
    depense.motif_annulation = motif[:255]
    depense.save(update_fields=['annule', 'motif_annulation'])
    return contre


def couts(bus=None, debut=None, fin=None):
    """Totaux des dépenses non annulées : général, par type, par bus (décroissant), par mois."""
    qs = DepenseTransport.objects.filter(annule=False).select_related('bus')
    if bus is not None:
        qs = qs.filter(bus=bus)
    if debut:
        qs = qs.filter(date__gte=debut)
    if fin:
        qs = qs.filter(date__lte=fin)
    total, par_type, par_mois = Decimal('0'), defaultdict(Decimal), defaultdict(Decimal)
    par_bus = {}
    for d in qs:
        total += d.montant
        par_type[d.type] += d.montant
        par_mois[d.date.strftime('%Y-%m')] += d.montant
        ligne = par_bus.setdefault(d.bus_id, {'bus': d.bus_id, 'numero': d.bus.numero, 'total': Decimal('0')})
        ligne['total'] += d.montant
    return {'total': total, 'par_type': dict(par_type), 'par_mois': dict(sorted(par_mois.items())),
            'par_bus': sorted(par_bus.values(), key=lambda l: (-l['total'], l['numero']))}
