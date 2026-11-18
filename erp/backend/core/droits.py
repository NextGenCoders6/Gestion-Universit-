"""Droits par module, sur le modèle d'Odoo.

Chaque module a ses niveaux ; un niveau = un groupe Django nommé
« <module>_<niveau> ». Le superuser a tous les niveaux de tous les modules.
Les rôles contextuels (enseignant, chef de département…) se déduisent des
données, pas des groupes.
"""
from django.contrib.auth.models import Group

MODULES = {
    'scolarite': {'libelle': 'Scolarité', 'niveaux': ['secretariat', 'faculte']},
    'edt': {'libelle': 'Emploi du temps', 'niveaux': ['utilisateur', 'responsable']},
    'rh': {'libelle': 'Ressources humaines', 'niveaux': ['utilisateur', 'responsable']},
    'finance': {'libelle': 'Finance', 'niveaux': ['utilisateur', 'responsable']},
    'logistique': {'libelle': 'Logistique', 'niveaux': ['utilisateur', 'responsable']},
    'parametres': {'libelle': 'Paramètres', 'niveaux': ['responsable']},
}


def nom_groupe(module, niveau):
    return f'{module}_{niveau}'


def tous_les_groupes():
    return [nom_groupe(code, niveau) for code, m in MODULES.items() for niveau in m['niveaux']]


def _groupes_de(user):
    if not getattr(user, 'is_authenticated', False):
        return set()
    cache = getattr(user, '_groupes_erp', None)
    if cache is None:
        cache = set(user.groups.values_list('name', flat=True))
        user._groupes_erp = cache
    return cache


def niveaux_utilisateur(user, module):
    niveaux = MODULES[module]['niveaux']
    if getattr(user, 'is_superuser', False):
        return list(niveaux)
    groupes = _groupes_de(user)
    return [n for n in niveaux if nom_groupe(module, n) in groupes]


def a_droit(user, module, niveau=None):
    niveaux = niveaux_utilisateur(user, module)
    return bool(niveaux) if niveau is None else niveau in niveaux


def modules_accessibles(user):
    resultat = []
    for code, m in MODULES.items():
        niveaux = niveaux_utilisateur(user, code)
        if niveaux:
            resultat.append({'code': code, 'libelle': m['libelle'], 'niveaux': niveaux})
    return resultat


def definir_droits(user, groupes):
    """Remplace les droits ERP de l'utilisateur par la liste donnée."""
    connus = set(tous_les_groupes())
    inconnus = [g for g in groupes if g not in connus]
    if inconnus:
        raise ValueError(f'Groupe(s) inconnu(s) : {", ".join(inconnus)}')
    user.groups.remove(*user.groups.filter(name__in=connus))
    user.groups.add(*Group.objects.filter(name__in=groupes))
    user._groupes_erp = None


def faculte_rattachee(user):
    rattachement = getattr(user, 'rattachement_faculte', None) if user and user.pk else None
    return rattachement.faculte if rattachement else None


# ── Rôles contextuels ────────────────────────────────────────────
# Chaque fonction reçoit l'utilisateur et renvoie un nom de rôle ou None.
# Les modules peuvent en ajouter (ex. « referent_classe » avec l'EDT).

def _personne(user):
    return getattr(user, 'personne', None) if user and user.pk else None


def _role_etudiant(user):
    p = _personne(user)
    return 'etudiant' if p is not None and hasattr(p, 'etudiant') else None


def _role_enseignant(user):
    p = _personne(user)
    return 'enseignant' if p is not None and hasattr(p, 'enseignant') else None


def _role_chef(user):
    p = _personne(user)
    if p is not None and hasattr(p, 'enseignant') and p.enseignant.departements_diriges.exists():
        return 'chef_departement'
    return None


def _role_employe(user):
    p = _personne(user)
    return 'employe' if p is not None and hasattr(p, 'employe') else None


ROLES_CONTEXTUELS = [_role_etudiant, _role_enseignant, _role_chef, _role_employe]


def roles_contextuels(user):
    return [r for r in (fn(user) for fn in ROLES_CONTEXTUELS) if r]
