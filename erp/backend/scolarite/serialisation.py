"""Mise en forme JSON des lignes du moteur."""


def ec_json(e):
    ec = e['ec']
    return {'id': ec.pk, 'code': ec.code, 'libelle': ec.libelle, 'credits': ec.credits, 'note': e['note'],
            'devoir': e['devoir'], 'session': e['session'], 'sr': e['sr'], 'absent': e['absent'],
            'non_saisi': e['non_saisi']}


def ligne_json(ligne):
    inscription = ligne['inscription']
    etudiant = inscription.etudiant
    return {
        'inscription': inscription.pk, 'etudiant': etudiant.pk, 'matricule': etudiant.matricule,
        'nom_complet': etudiant.personne.nom_complet, 'moyenne': ligne['moyenne'],
        'eliminatoire': ligne['eliminatoire'], 'decision': ligne['decision'], 'mention': ligne['mention'],
        'credits_valides': ligne['credits_valides'], 'credits_totaux': ligne['credits_totaux'],
        'ecs_non_saisis': ligne['ecs_non_saisis'], 'rang': ligne['rang'],
        'ues': [{'id': b['ue'].pk, 'code': b['ue'].code, 'libelle': b['ue'].libelle, 'moyenne_ue': b['moyenne_ue'],
                 'credits_ue': b['credits_ue'], 'credits_ue_total': b['credits_ue_total'], 'validee': b['validee'],
                 'ecs': [ec_json(e) for e in b['ecs']]} for b in ligne['ues']],
    }


def programme_json(prog):
    return [{'id': ue.pk, 'code': ue.code, 'libelle': ue.libelle,
             'ecs': [{'id': ec.pk, 'code': ec.code, 'libelle': ec.libelle, 'credits': ec.credits} for ec in ecs]}
            for ue, ecs in prog]


def resultat_json(r):
    if r is None:
        return None
    return {'moyenne': float(r.moyenne), 'credits_obtenus': r.credits_obtenus, 'credits_totaux': r.credits_totaux,
            'decision': r.decision, 'mention': r.mention, 'rang': r.rang, 'delibere_le': r.delibere_le}
