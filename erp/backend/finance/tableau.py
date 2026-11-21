"""Indicateurs des frais de scolarité d'une année : partagés par le tableau de bord Finance et le launchpad."""
from decimal import Decimal

from finance import frais as service_frais
from finance.models import FraisScolarite


def indicateurs_frais(annee):
    """Montants attendus et encaissés, retards, dossiers sans tarif et trop-perçus de l'année.

    `taux_recouvrement` vaut None quand rien n'est attendu (taux incalculable).
    """
    dossiers = list(FraisScolarite.objects.filter(inscription__annee=annee).exclude(
        inscription__statut='abandonnee').prefetch_related('echeances')) if annee else []
    attendus = sum((d.montant_du for d in dossiers), Decimal('0'))
    encaisses = sum((min(d.montant_paye, d.montant_du) for d in dossiers), Decimal('0'))
    retards = [service_frais.montant_en_retard(d, echeances=list(d.echeances.all())) for d in dossiers]
    return {
        'frais_attendus': attendus,
        'frais_encaisses': encaisses,
        'taux_recouvrement': round(float(encaisses / attendus * 100), 1) if attendus else None,
        'dossiers': len(dossiers),
        'dossiers_en_retard': sum(1 for r in retards if r > 0),
        'montant_en_retard': sum(retards, Decimal('0')),
        'dossiers_sans_tarif': sum(1 for d in dossiers if d.montant_du == 0 and not d.montant_ajuste),
        'trop_percus': sum(1 for d in dossiers if d.trop_percu > 0),
        'montant_trop_percu': sum((d.trop_percu for d in dossiers), Decimal('0')),
    }
