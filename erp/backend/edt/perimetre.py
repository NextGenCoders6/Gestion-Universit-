"""Périmètre de classes d'un utilisateur dans l'EDT (port de EDT_app/perimetre.py).

- superuser, edt_responsable : illimité (None) en lecture et en écriture ;
- edt_utilisateur : lecture illimitée, aucune écriture ;
- chef de département : classes à filière de ses départements dirigés ;
- référent : ses classes assignées ;
- les deux s'additionnent.
"""
from django.db.models import Q

from core.droits import a_droit
from core.models import Classe
from edt.droits import enseignant_de


def _illimite(user):
    return user.is_superuser or a_droit(user, 'edt', 'responsable')


def _perimetre_personnel(user):
    ens = enseignant_de(user)
    if ens is None:
        return Classe.objects.none()
    q = Q(pk__in=[])
    dirigés = ens.departements_diriges.all()
    if dirigés.exists():
        q |= Q(filiere__departement__in=dirigés)
    ref = getattr(ens, 'referent_classes', None)
    if ref is not None:
        q |= Q(pk__in=ref.classes.values_list('pk', flat=True))
    return Classe.objects.filter(q).distinct()


def classes_gerables(user):
    """Classes dont l'utilisateur peut modifier l'emploi du temps (None = toutes)."""
    if _illimite(user):
        return None
    return _perimetre_personnel(user)


def classes_autorisees(user):
    """Classes dont l'utilisateur peut consulter l'emploi du temps (None = toutes)."""
    if _illimite(user) or a_droit(user, 'edt', 'utilisateur'):
        return None
    return _perimetre_personnel(user)


def filtrer_par_classes(qs, classes, champ='classe'):
    return qs if classes is None else qs.filter(**{f'{champ}__in': classes})


def peut_gerer_classe(user, classe):
    classes = classes_gerables(user)
    return classes is None or classes.filter(pk=classe.pk).exists()


def restreindre_enseignants(user, qs):
    """Liste complète pour un gestionnaire (affectations inter-départements), département sinon."""
    if _illimite(user) or a_droit(user, 'edt'):
        return qs
    ens = enseignant_de(user)
    if ens is None:
        return qs.none()
    return qs.filter(departement=ens.departement_id)
