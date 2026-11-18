import { describe, expect, it } from 'vitest';
import { menuVisible, moduleParCode } from '@/app/modules';

describe('Scolarité — menu selon le niveau', () => {
  const module = moduleParCode('scolarite');
  const libelles = (niveaux) => menuVisible(module, niveaux).map((m) => m.libelle);

  it('le secrétariat ne voit ni la saisie ni les délibérations', () => {
    expect(libelles(['secretariat'])).toEqual(['Étudiants']);
  });

  it('la faculté voit tout', () => {
    expect(libelles(['faculte'])).toEqual(['Étudiants', 'Saisie des notes', 'Délibérations', 'Promotion et orientation']);
  });
});
