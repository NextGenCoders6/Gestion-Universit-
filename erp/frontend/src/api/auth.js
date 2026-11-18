import apiClient from './client';
import useAuthStore from '@/store/authStore';

/** Connexion : renvoie { access, refresh, user } où user a la forme de /api/core/moi/. */
export async function login(username, password) {
  const response = await apiClient.post('/core/token/', { username, password });
  return response.data;
}

/** Profil à jour (droits relus à chaque appel). */
export async function fetchMoi() {
  const response = await apiClient.get('/core/moi/');
  return response.data;
}

/** Déconnexion : le serveur invalide le refresh token, puis la session locale est vidée. */
export async function logout() {
  const { refreshToken, clearAuth } = useAuthStore.getState();
  try {
    if (refreshToken) await apiClient.post('/core/deconnexion/', { refresh: refreshToken });
  } catch {
    // Serveur injoignable : la session locale est vidée quand même.
  } finally {
    clearAuth();
  }
}
