import { describe, expect, it } from 'vitest';
import { echeancier } from './echeancier';

describe('échéancier (aperçu côté écran)', () => {
  it('reprend la règle du serveur', () => {
    const l = echeancier(1500000, 10, '2026-10', 5);
    expect(l).toHaveLength(10);
    expect(l[0]).toEqual({ mois: '2026-10', date_limite: '2026-11-05', montant: 150000 });
    expect(l[9]).toEqual({ mois: '2027-07', date_limite: '2027-08-05', montant: 150000 });
    expect(echeancier(1500000, 7, '2026-10', 5).map((x) => x.montant)).toEqual([214285, 214285, 214285, 214285, 214285, 214285, 214290]);
    expect(echeancier(0, 10, '2026-10', 5)).toEqual([]);
  });
});
