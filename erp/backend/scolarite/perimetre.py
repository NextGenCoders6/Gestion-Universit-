"""Périmètre de la Scolarité : un utilisateur rattaché à une faculté ne voit qu'elle."""
from django.db.models import Q

from core.droits import faculte_rattachee
from core.models import Faculte


def facultes_autorisees(user):
    """QuerySet des facultés visibles, ou None si l'utilisateur les voit toutes."""
    faculte = faculte_rattachee(user)
    return None if faculte is None else Faculte.objects.filter(pk=faculte.pk)


def q_classe_de_faculte(faculte, prefixe=''):
    """Q sélectionnant les classes (ou objets liés via `prefixe`) d'une faculté."""
    return (Q(**{f'{prefixe}portail__faculte': faculte})
            | Q(**{f'{prefixe}filiere__departement__faculte': faculte}))


def restreindre_par_faculte(qs, user, prefixe=''):
    """Limite `qs` à la faculté de rattachement ; `prefixe` mène à la classe (ex. 'classe__')."""
    faculte = faculte_rattachee(user)
    return qs if faculte is None else qs.filter(q_classe_de_faculte(faculte, prefixe)).distinct()
