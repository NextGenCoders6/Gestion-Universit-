import { describe, expect, it } from 'vitest';
import { REGISTRE, menuVisible, moduleParCode, modulesVisibles } from './modules';

describe('registre des modules', () => {
  it('modulesVisibles filtre et ordonne selon le registre', () => {
    const moi = { modules: [{ code: 'finance', niveaux: ['utilisateur'] }, { code: 'rh', niveaux: ['responsable'] }] };
    expect(modulesVisibles(moi).map((m) => m.code)).toEqual(['rh', 'finance']);
  });

  it('modulesVisibles ignore un code inconnu du frontend', () => {
    expect(modulesVisibles({ modules: [{ code: 'inconnu', niveaux: ['x'] }] })).toEqual([]);
  });

  it('modulesVisibles sans profil', () => {
    expect(modulesVisibles(null)).toEqual([]);
  });

  it('chaque module du backend a une entrée', () => {
    expect(REGISTRE.map((m) => m.code)).toEqual(['scolarite', 'edt', 'rh', 'finance', 'logistique', 'parametres']);
  });

  it('menuVisible filtre par niveau', () => {
    const module = {
      menu: [
        { chemin: 'a', libelle: 'A' },
        { chemin: 'b', libelle: 'B', niveaux: ['responsable'] },
      ],
    };
    expect(menuVisible(module, ['utilisateur']).map((i) => i.chemin)).toEqual(['a']);
    expect(menuVisible(module, ['responsable']).map((i) => i.chemin)).toEqual(['a', 'b']);
  });

  it('moduleParCode', () => {
    expect(moduleParCode('parametres').libelle).toBe('Paramètres');
    expect(moduleParCode('xyz')).toBeUndefined();
  });
});
