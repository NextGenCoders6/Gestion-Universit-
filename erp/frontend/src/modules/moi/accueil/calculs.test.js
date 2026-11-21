import { describe, expect, it } from 'vitest';
import {
  bilanEnseignements, debutFin, dernierResultat, dossierCourant, heuresSeances, prochainesSeances,
} from './calculs';

const s = (jour, debut, fin, extra = {}) => ({ id: `${jour}${debut}`, creneau_effectif: { jour, debut, fin }, ...extra });

describe('calculs de l’accueil', () => {
  it('lit le créneau effectif, à défaut la date de la séance', () => {
    expect(debutFin(s('2026-11-25', '08:00', '10:00')).debut).toEqual(new Date(2026, 10, 25, 8, 0));
    expect(debutFin({ date_seance: '2026-11-18', heure_debut: '14:00', heure_fin: '15:30' }).fin)
      .toEqual(new Date(2026, 10, 18, 15, 30));
  });

  it('additionne les heures de cours', () => {
    expect(heuresSeances([s('2026-11-16', '09:00', '11:00'), s('2026-11-17', '14:00', '15:30')])).toBe(3.5);
    expect(heuresSeances([])).toBe(0);
  });

  it('trie les prochaines séances sur le créneau effectif (séance reportée)', () => {
    const reportee = s('2026-11-25', '08:00', '10:00', { date_seance: '2026-11-18', heure_debut: '08:00', heure_fin: '10:00' });
    expect(prochainesSeances([reportee, s('2026-11-24', '09:00', '11:00')], new Date(2026, 10, 21)).map((x) => x.id))
      .toEqual(['2026-11-2409:00', '2026-11-2508:00']);
  });

  it('écarte une séance terminée, garde une séance en cours', () => {
    const seances = [s('2026-11-21', '08:00', '10:00'), s('2026-11-21', '10:00', '12:00')];
    expect(prochainesSeances(seances, new Date(2026, 10, 21, 11)).map((x) => x.id)).toEqual(['2026-11-2110:00']);
  });

  it('garde les 5 premières', () => {
    const seances = Array.from({ length: 8 }, (_, i) => s(`2026-11-2${i + 2}`, '09:00', '10:00'));
    expect(prochainesSeances(seances, new Date(2026, 10, 21))).toHaveLength(5);
  });

  it('donne le dernier semestre délibéré', () => {
    expect(dernierResultat({ inscriptions: [] })).toBeNull();
    expect(dernierResultat(undefined)).toBeNull();
    expect(dernierResultat({ inscriptions: [{ resultats_masques: false, semestres: [
      { semestre: 'S1', deliberee: true, resultat: { moyenne: 6.98, decision: 'AJOURNÉ' } },
      { semestre: 'S2', deliberee: false, resultat: null }] }] }))
      .toEqual({ semestre: 'S1', moyenne: 6.98, decision: 'AJOURNÉ' });
    expect(dernierResultat({ inscriptions: [{ resultats_masques: false, semestres: [{ semestre: 'S1', deliberee: false }] }] }))
      .toBeNull();
  });

  it('ne révèle pas des résultats masqués', () => {
    expect(dernierResultat({ inscriptions: [{ resultats_masques: true, message_resultats: 'Réglez vos frais.', semestres: [
      { semestre: 'S1', deliberee: true, resultat: { moyenne: 12, decision: 'ADMIS' } }] }] }))
      .toEqual({ masque: 'Réglez vos frais.' });
  });

  it('choisit le dossier de frais de l’inscription active', () => {
    expect(dossierCourant([{ id: 1, inscription_statut: 'terminee' }, { id: 2, inscription_statut: 'active' }]).id).toBe(2);
    expect(dossierCourant([{ id: 1, inscription_statut: 'terminee' }]).id).toBe(1);
    expect(dossierCourant([])).toBeNull();
    expect(dossierCourant(undefined)).toBeNull();
  });

  it('fait le bilan des enseignements', () => {
    expect(bilanEnseignements([
      { classe: 1, heures_effectuees: 6, heures_prevues: 24 },
      { classe: 1, heures_effectuees: 12, heures_prevues: 48 },
      { classe: 3, heures_effectuees: 4, heures_prevues: 4 },
    ])).toEqual({ faites: 22, prevues: 76, classes: 2 });
    expect(bilanEnseignements([])).toEqual({ faites: 0, prevues: 0, classes: 0 });
  });
});
