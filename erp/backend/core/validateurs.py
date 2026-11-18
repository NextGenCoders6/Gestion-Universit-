"""Validateurs communs, repris de uccb_backend/gestion_eleves/models.py."""
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

nom_validator = RegexValidator(r'^[a-zA-ZÀ-ÿ\s\-]+$', 'Lettres, espaces et tirets uniquement.')


def valider_date_naissance(valeur):
    """La personne doit avoir entre 10 et 80 ans."""
    aujourd_hui = date.today()
    if valeur > aujourd_hui:
        raise ValidationError('La date de naissance ne peut pas être dans le futur.')
    age = aujourd_hui.year - valeur.year - ((aujourd_hui.month, aujourd_hui.day) < (valeur.month, valeur.day))
    if age < 10:
        raise ValidationError(f'Date de naissance invalide : la personne aurait {age} an(s).')
    if age > 80:
        raise ValidationError(f'Date de naissance invalide : {age} ans est trop élevé.')
