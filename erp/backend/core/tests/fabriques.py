"""Fabriques de données de test du socle, réutilisées par tous les modules."""
from datetime import date

from core.models import (
    AnneeAcademique, Classe, Departement, ElementConstitutif, Faculte, Filiere,
    Parcours, Periode, Portail, UniteEnseignement,
)


def annee(libelle='2026-2027', en_cours=False, **kwargs):
    debut = int(libelle[:4])
    obj, _ = AnneeAcademique.objects.get_or_create(
        libelle=libelle,
        defaults={
            'date_debut': kwargs.pop('date_debut', date(debut, 10, 1)),
            'date_fin': kwargs.pop('date_fin', date(debut + 1, 7, 31)),
            **kwargs,
        },
    )
    if en_cours:
        obj.en_cours = True
        obj.save()
    return obj


def periode(a=None, numero=1):
    a = a or annee()
    debut = a.date_debut.year
    if numero == 1:
        return Periode.objects.create(annee=a, numero=1, date_debut=date(debut, 10, 1), date_fin=date(debut + 1, 2, 15))
    return Periode.objects.create(annee=a, numero=2, date_debut=date(debut + 1, 2, 16), date_fin=date(debut + 1, 7, 31))


def faculte(code='FST', nom=None):
    obj, _ = Faculte.objects.get_or_create(code=code, defaults={'nom': nom or f'Faculté {code}'})
    return obj


def departement(fac=None, libelle='Informatique'):
    fac = fac or faculte()
    obj, _ = Departement.objects.get_or_create(faculte=fac, libelle=libelle)
    return obj


def portail(fac=None, code='MIP'):
    fac = fac or faculte()
    obj, _ = Portail.objects.get_or_create(faculte=fac, code=code, defaults={'nom': f'Portail {code}'})
    return obj


def filiere(dep=None, port=None, code='INFO'):
    dep = dep or departement()
    port = port or portail(dep.faculte)
    obj, _ = Filiere.objects.get_or_create(
        departement=dep, code=code, defaults={'portail': port, 'nom': f'Filière {code}'}
    )
    return obj


def parcours(type_parcours='Licence', niveau=1):
    obj, _ = Parcours.objects.get_or_create(type_parcours=type_parcours, niveau=niveau)
    return obj


def classe_l1(a=None, port=None):
    return Classe.objects.create(annee=a or annee(), parcours=parcours('Licence', 1), portail=port or portail())


def ue(code='UE-MIP-11', semestre='S1', port=None, fil=None):
    if fil is None and port is None:
        port = portail()
    return UniteEnseignement.objects.create(code=code, libelle=f'UE {code}', semestre=semestre, portail=port, filiere=fil)


def ec(u=None, code='EC-ALGO', credits=3, dep=None):
    return ElementConstitutif.objects.create(
        ue=u or ue(), code=code, libelle=f'EC {code}', credits=credits, departement=dep or departement(),
    )
