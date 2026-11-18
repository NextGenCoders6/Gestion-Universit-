import { useEffect } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { fetchMoi } from '@/api/auth';
import useAuthStore from '@/store/authStore';

/**
 * Exige une session. À chaque changement de page, relit le profil
 * (/api/core/moi/) : les droits retirés ou ajoutés depuis la connexion prennent
 * effet, et un compte suspendu entre-temps est renvoyé au login (le client API
 * traite la réponse 403 « profil_suspendu »).
 */
export default function RequireAuth() {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);
  const deconnexionVolontaire = useAuthStore((state) => state.deconnexionVolontaire);
  const location = useLocation();

  useEffect(() => {
    if (!isAuthenticated) return;
    fetchMoi()
      .then((moi) => useAuthStore.getState().setUser(moi))
      .catch(() => {
        // Erreur réseau : on garde le profil connu ; un 401/403 de session est
        // déjà traité par le client API (déconnexion).
      });
  }, [isAuthenticated, location.pathname]);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={deconnexionVolontaire ? undefined : { from: location }} />;
  }
  return <Outlet />;
}
