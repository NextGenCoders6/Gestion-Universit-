"""Écriture au journal des opérations (numérotation par année, montants validés)."""
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.utils import timezone

from finance.models import MODES_PAIEMENT, Compteur, Operation

MAXI = Decimal('9999999999')


def montant_valide(valeur, *, positif=True, champ='montant'):
    try:
        d = Decimal(str(valeur).strip().replace(' ', '').replace(',', '.'))
    except (InvalidOperation, ValueError):
        raise ValidationError({champ: 'Montant invalide.'})
    if not d.is_finite() or abs(d) > MAXI:
        raise ValidationError({champ: 'Montant invalide.'})
    if positif and d <= 0:
        raise ValidationError({champ: 'Le montant doit être positif.'})
    if d.as_tuple().exponent < -2:
        raise ValidationError({champ: 'Deux décimales au plus.'})
    return d


def date_valide(jour, champ='date'):
    jour = jour or timezone.localdate()
    if jour > timezone.localdate():
        raise ValidationError({champ: 'La date ne peut pas être dans le futur.'})
    return jour


def mode_valide(mode):
    if mode not in dict(MODES_PAIEMENT):
        raise ValidationError({'mode': 'Mode de paiement invalide.'})
    return mode


def prochain_numero(jour):
    """« OP-AAAA-000001 » : compteur par année, verrouillé (appel dans une transaction)."""
    compteur, _ = Compteur.objects.select_for_update().get_or_create(cle=f'operation-{jour.year}')
    compteur.valeur += 1
    compteur.save(update_fields=['valeur'])
    return f'OP-{jour.year}-{compteur.valeur:06d}'


def ecrire(libelle, montant, categorie, jour, par=None, annule=None):
    return Operation.objects.create(numero=prochain_numero(jour), date=jour, libelle=libelle[:255], montant=montant,
                                    categorie=categorie, par=par, annule=annule)
