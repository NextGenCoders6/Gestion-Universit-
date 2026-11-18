"""Moteur de calcul des résultats — port de l'ancienne scolarité (engine.py), règles inchangées.

1. Note éliminatoire : moyenne d'EC saisie < 6/20 (absent compte 0, non saisi ignoré).
2. ADMIS : moyenne du semestre ≥ 10 et aucune note éliminatoire.
3. ADMIS → tous les crédits du semestre acquis (compensation entre UE) ;
   sinon une UE est validée si sa moyenne est ≥ 6.
4. Un EC sans note saisie est ignoré du calcul (il n'est pas compté 0).
"""
from collections import defaultdict
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from scolarite.models import Note, ResultatSemestre


def mention(moyenne):
    if moyenne < 10:
        return 'NÉANT'
    if moyenne < 12:
        return 'PASSABLE'
    if moyenne < 14:
        return 'ASSEZ BIEN'
    if moyenne < 16:
        return 'BIEN'
    return 'TRÈS BIEN'


def programme(classe, semestre):
    """[(ue, [ec, …]), …] du semestre pour la classe, triés par code. ValueError si hors niveau."""
    if semestre not in classe.semestres:
        raise ValueError(f"Le semestre {semestre} n'appartient pas au niveau {classe.parcours.code}.")
    par_ue = {}
    for ec in classe.ecs_au_programme().filter(ue__semestre=semestre).order_by('ue__code', 'code'):
        par_ue.setdefault(ec.ue_id, (ec.ue, []))[1].append(ec)
    return list(par_ue.values())


def _flottant(valeur):
    return None if valeur is None else float(valeur)


def _ligne(inscription, prog, notes):
    """notes : {ec_id: Note} de l'inscription pour ce semestre."""
    ligne = {
        'inscription': inscription, 'ues': [], 'moyenne': 0.0, 'eliminatoire': False,
        'decision': 'AJOURNÉ', 'mention': 'NÉANT', 'credits_valides': 0, 'credits_totaux': 0,
        'ecs_non_saisis': [], 'rang': None,
    }
    points, credits = 0.0, 0
    for ue, ecs in prog:
        bloc = {'ue': ue, 'ecs': [], 'moyenne_ue': 0.0, 'credits_ue': 0,
                'credits_ue_total': sum(ec.credits for ec in ecs), 'validee': False}
        points_ue, credits_ue = 0.0, 0
        for ec in ecs:
            note = notes.get(ec.pk)
            valeur = _flottant(note.moyenne) if note else None
            if valeur is None:
                ligne['ecs_non_saisis'].append(ec.code)
            else:
                if valeur < 6:
                    ligne['eliminatoire'] = True
                points_ue += valeur * ec.credits
                credits_ue += ec.credits
            bloc['ecs'].append({
                'ec': ec, 'note': valeur, 'non_saisi': valeur is None,
                'devoir': _flottant(note.note_devoir) if note else None,
                'session': _flottant(note.note_session) if note else None,
                'sr': _flottant(note.note_sr) if note else None,
                'absent': bool(note and note.est_absent),
            })
        ligne['credits_totaux'] += bloc['credits_ue_total']
        if credits_ue:
            bloc['moyenne_ue'] = round(points_ue / credits_ue, 2)
            bloc['credits_ue'] = credits_ue
            points += points_ue
            credits += credits_ue
        ligne['ues'].append(bloc)

    if credits:
        moyenne = round(points / credits, 2)
        ligne['moyenne'] = moyenne
        if not ligne['eliminatoire'] and moyenne >= 10:
            ligne['decision'] = 'ADMIS'
            ligne['mention'] = mention(moyenne)
            ligne['credits_valides'] = ligne['credits_totaux']
            for bloc in ligne['ues']:
                bloc['validee'] = True
        else:
            for bloc in ligne['ues']:
                bloc['validee'] = bloc['credits_ue'] > 0 and bloc['moyenne_ue'] >= 6
            ligne['credits_valides'] = sum(b['credits_ue'] for b in ligne['ues'] if b['validee'])
    return ligne


def ligne_etudiant(inscription, semestre):
    """Résultat calculé d'une inscription pour un semestre de son niveau."""
    prog = programme(inscription.classe, semestre)
    notes = {n.ec_id: n for n in inscription.notes.filter(ec__ue__semestre=semestre)}
    return _ligne(inscription, prog, notes)


def deliberation(classe, semestre, *, enregistrer=False, par=None):
    """Lignes de toutes les inscriptions non abandonnées de la classe, classées par moyenne décroissante."""
    prog = programme(classe, semestre)
    inscriptions = list(classe.inscriptions.exclude(statut='abandonnee')
                        .select_related('etudiant__personne', 'classe__parcours'))
    notes = defaultdict(dict)
    for n in Note.objects.filter(inscription__in=inscriptions, ec__ue__semestre=semestre):
        notes[n.inscription_id][n.ec_id] = n
    lignes = [_ligne(i, prog, notes[i.pk]) for i in inscriptions]
    lignes.sort(key=lambda l: l['moyenne'], reverse=True)
    for rang, ligne in enumerate(lignes, start=1):
        ligne['rang'] = rang
    if enregistrer:
        enregistrer_resultats(lignes, semestre, par)
    return lignes


@transaction.atomic
def enregistrer_resultats(lignes, semestre, par=None):
    maintenant = timezone.now()
    for ligne in lignes:
        if not ligne['credits_totaux']:
            continue
        ResultatSemestre.objects.update_or_create(
            inscription=ligne['inscription'], semestre=semestre,
            defaults={
                'moyenne': Decimal(str(ligne['moyenne'])), 'credits_obtenus': ligne['credits_valides'],
                'credits_totaux': ligne['credits_totaux'], 'decision': ligne['decision'],
                'mention': ligne['mention'], 'rang': ligne['rang'],
                'delibere_le': maintenant, 'delibere_par': par,
            },
        )
