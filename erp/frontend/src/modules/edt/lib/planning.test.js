import { describe, expect, it, vi } from 'vitest';
import { deplacerSeance, enIso, evenementsDepuisSeances } from './planning';

const seance = (extra = {}) => ({
  id: 7, ec_code: 'BDD', ec_libelle: 'Bases de données', classe_libelle: 'L2 INFO', enseignant_nom: 'MBEMBA C.',
  type_seance: 'CM', statut: 'Confirmée', seance_liee: null,
  creneau_effectif: { jour: '2026-10-05', debut: '09:00', fin: '11:00' }, ...extra,
});

describe('evenementsDepuisSeances', () => {
  it('place la séance sur son créneau effectif', () => {
    const [e] = evenementsDepuisSeances([seance({ statut: 'Reportée', creneau_effectif: { jour: '2026-10-06', debut: '14:15', fin: '16:15' } })]);
    expect(e).toMatchObject({ id: '7', start: '2026-10-06T14:15', end: '2026-10-06T16:15', title: 'BDD — L2 INFO' });
    expect(e.extendedProps.heure_debut).toBe('14:15');
  });

  it('déplaçable seulement si on gère et que la séance est en brouillon ou confirmée', () => {
    const [a, b] = evenementsDepuisSeances([seance(), seance({ id: 8, statut: 'Annulée' })], { modifiable: true });
    expect(a.startEditable).toBe(true);
    expect(b.startEditable).toBe(false);
    expect(evenementsDepuisSeances([seance()], { modifiable: false })[0].startEditable).toBe(false);
  });

  it('signale les cours mutualisés', () => {
    expect(evenementsDepuisSeances([seance({ seance_liee: 3 })])[0].extendedProps.is_mutualise).toBe(true);
  });
});

describe('deplacerSeance', () => {
  const info = () => ({
    event: { id: '7', start: new Date(2026, 9, 11, 9, 0), end: new Date(2026, 9, 11, 11, 0) },
    revert: vi.fn(),
  });

  it('envoie la nouvelle date et les nouvelles heures', async () => {
    const modifier = vi.fn().mockResolvedValue({});
    const i = info();
    expect(await deplacerSeance(i, { modifier, notifier: vi.fn() })).toBe(true);
    expect(modifier).toHaveBeenCalledWith('7', { date_seance: '2026-10-11', heure_debut: '09:00', heure_fin: '11:00' });
    expect(i.revert).not.toHaveBeenCalled();
  });

  it('remet la séance en place et affiche le message du serveur si le déplacement est refusé', async () => {
    const modifier = vi.fn().mockRejectedValue({
      response: { status: 400, data: { date_seance: ['Impossible de planifier une séance un dimanche.'] } },
    });
    const notifier = vi.fn();
    const i = info();
    expect(await deplacerSeance(i, { modifier, notifier })).toBe(false);
    expect(i.revert).toHaveBeenCalled();
    expect(notifier).toHaveBeenCalledWith(expect.objectContaining({
      description: 'Impossible de planifier une séance un dimanche.', variant: 'destructive',
    }));
  });
});

describe('enIso', () => {
  it('date locale sans décalage de fuseau', () => {
    expect(enIso(new Date(2026, 0, 31, 23, 30))).toBe('2026-01-31');
  });
});
