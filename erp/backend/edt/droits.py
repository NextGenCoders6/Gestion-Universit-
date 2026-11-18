"""Rôles et niveaux contextuels apportés par le module EDT (enregistrés dans edt.apps)."""


def enseignant_de(user):
    personne = getattr(user, 'personne', None) if user and user.pk else None
    return getattr(personne, 'enseignant', None) if personne is not None else None


def est_referent(enseignant):
    ref = getattr(enseignant, 'referent_classes', None) if enseignant is not None else None
    return ref is not None and ref.classes.exists()


def est_chef(enseignant):
    return enseignant is not None and enseignant.departements_diriges.exists()


def role_referent(user):
    return 'referent_classe' if est_referent(enseignant_de(user)) else None


def niveaux_edt(user):
    """Un chef de département ou un référent gère l'EDT de son périmètre."""
    ens = enseignant_de(user)
    return {'edt': ['perimetre']} if (est_chef(ens) or est_referent(ens)) else {}
