import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuthStore from '@/store/authStore';
import { queryClient } from '@/lib/queryClient';
import { logout } from './auth';

vi.mock('./client', () => ({ default: { post: vi.fn(() => Promise.resolve({})) } }));

describe('logout', () => {
  beforeEach(() => {
    useAuthStore.getState().setAuth({ accessToken: 'a', refreshToken: 'r', user: { id: 1, modules: [] } });
  });

  it('vide la session et le cache des données du compte précédent', async () => {
    queryClient.setQueryData(['parametres', 'personnes', {}], [{ id: 1, nom: 'Secret' }]);
    await logout();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(queryClient.getQueryData(['parametres', 'personnes', {}])).toBeUndefined();
    expect(useAuthStore.getState().deconnexionVolontaire).toBe(true);
  });

  it('une nouvelle connexion efface le marqueur de déconnexion', async () => {
    await logout();
    useAuthStore.getState().setAuth({ accessToken: 'b', refreshToken: 's', user: { id: 2, modules: [] } });
    expect(useAuthStore.getState().deconnexionVolontaire).toBe(false);
  });
});
