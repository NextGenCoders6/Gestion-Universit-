import { beforeEach, describe, expect, it } from 'vitest';
import useAuthStore, { aDroit, aRole, selectModules } from './authStore';

const get = () => useAuthStore.getState();
const moi = (modules, roles = []) => ({ id: 1, username: 'u', nom_complet: 'U', modules, roles });

describe('authStore', () => {
  beforeEach(() => get().clearAuth());

  it('aDroit sans niveau', () => {
    get().setAuth({ accessToken: 'a', refreshToken: 'r', user: moi([{ code: 'rh', niveaux: ['utilisateur'] }]) });
    expect(aDroit(get(), 'rh')).toBe(true);
    expect(aDroit(get(), 'finance')).toBe(false);
  });

  it('aDroit avec niveau', () => {
    get().setAuth({ accessToken: 'a', refreshToken: 'r', user: moi([{ code: 'rh', niveaux: ['utilisateur'] }]) });
    expect(aDroit(get(), 'rh', 'utilisateur')).toBe(true);
    expect(aDroit(get(), 'rh', 'responsable')).toBe(false);
  });

  it('aRole et selectModules', () => {
    get().setAuth({ accessToken: 'a', refreshToken: 'r', user: moi([], ['enseignant']) });
    expect(aRole(get(), 'enseignant')).toBe(true);
    expect(aRole(get(), 'etudiant')).toBe(false);
    expect(selectModules(get())).toEqual([]);
  });

  it('setUser remplace le profil sans toucher aux jetons', () => {
    get().setAuth({ accessToken: 'a', refreshToken: 'r', user: moi([]) });
    get().setUser(moi([{ code: 'finance', niveaux: ['responsable'] }]));
    expect(get().accessToken).toBe('a');
    expect(aDroit(get(), 'finance', 'responsable')).toBe(true);
  });

  it('clearAuth vide tout', () => {
    get().setAuth({ accessToken: 'a', refreshToken: 'r', user: moi([]) });
    get().clearAuth();
    expect(get().isAuthenticated).toBe(false);
    expect(get().user).toBeNull();
    expect(aDroit(get(), 'rh')).toBe(false);
  });
});
