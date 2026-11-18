"""Mise en forme JSON des dossiers, paiements, paies et opérations."""
from finance import frais as service_frais
from finance.models import MODES_PAIEMENT


def f(valeur):
    return None if valeur is None else float(valeur)


def echeance_json(e):
    return {**e, 'montant': f(e['montant']), 'paye': f(e['paye'])}


def dossier_json(d, detail=False):
    i = d.inscription
    echeances = list(d.echeances.all())
    etats = service_frais.etat_echeances(d, echeances=echeances)
    prochaine = next((e for e in etats if e['etat'] != 'payee'), None)
    retard = sum((e['montant'] - e['paye'] for e in etats if e['etat'] == 'en_retard'), 0)
    donnees = {
        'id': d.pk, 'inscription': i.pk, 'etudiant': i.etudiant_id, 'matricule': i.etudiant.matricule,
        'nom_complet': i.etudiant.personne.nom_complet, 'classe': i.classe_id, 'classe_libelle': i.classe.libelle,
        'annee': i.annee_id, 'annee_libelle': i.annee.libelle, 'inscription_statut': i.statut,
        'montant_du': f(d.montant_du), 'montant_paye': f(d.montant_paye), 'reste': f(d.reste),
        'trop_percu': f(d.trop_percu), 'statut': d.statut, 'montant_ajuste': d.montant_ajuste,
        'echeancier_adapte': d.echeancier_adapte, 'sans_tarif': d.montant_du == 0 and not d.montant_ajuste,
        'en_retard': retard > 0, 'montant_en_retard': f(retard),
        'prochaine_echeance': echeance_json(prochaine) if prochaine else None,
    }
    if detail:
        donnees['echeances'] = [echeance_json(e) for e in etats]
        donnees['paiements'] = [paiement_json(p) for p in d.paiements.select_related('operation', 'par')]
    return donnees


def paiement_json(p):
    return {'id': p.pk, 'date': p.date, 'montant': f(p.montant), 'mode': p.mode,
            'mode_libelle': dict(MODES_PAIEMENT)[p.mode], 'reference': p.reference, 'numero': p.operation.numero,
            'annule': p.annule, 'motif_annulation': p.motif_annulation,
            'par': p.par.get_username() if p.par else None}


def paie_json(p, detail=False):
    from finance.paie import libelle_paie
    personne = p.personne
    role = 'enseignant' if hasattr(personne, 'enseignant') else 'employe'
    donnees = {
        'id': p.pk, 'origine': p.origine, 'mois': p.mois, 'personne': personne.pk, 'nom_complet': personne.nom_complet,
        'role': role, 'libelle': libelle_paie(p), 'contrat': p.contrat_id, 'montant_du': f(p.montant_du),
        'montant_paye': f(p.montant_paye), 'reste': f(p.reste), 'statut': p.statut, 'montant_ajuste': p.montant_ajuste,
    }
    if detail:
        donnees['paiements'] = [paiement_json(x) for x in p.paiements.select_related('operation', 'par')]
    return donnees


def operation_json(o):
    return {'id': o.pk, 'numero': o.numero, 'date': o.date, 'libelle': o.libelle, 'montant': f(o.montant),
            'categorie': o.categorie, 'categorie_libelle': o.get_categorie_display(),
            'annule': o.annule_id, 'est_annulee': hasattr(o, 'annulation'),
            'par': o.par.get_username() if o.par else None}
