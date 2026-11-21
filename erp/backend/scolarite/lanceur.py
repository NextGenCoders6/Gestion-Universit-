"""Résumé Scolarité du launchpad : inscrits actifs de l'année en cours, dans le périmètre de la faculté."""
from core.lanceur import entree
from core.models import AnneeAcademique
from scolarite.models import Inscription
from scolarite.perimetre import restreindre_par_faculte


def resume(request):
    annee = AnneeAcademique.courante()
    if annee is None:
        return entree('scolarite', libelle='étudiants inscrits', detail='Aucune année en cours')
    inscrits = restreindre_par_faculte(Inscription.objects.filter(annee=annee, statut='active'), request.user,
                                       prefixe='classe__')
    return entree('scolarite', valeur=inscrits.count(), libelle='étudiants inscrits', detail=f'Année {annee.libelle}')
