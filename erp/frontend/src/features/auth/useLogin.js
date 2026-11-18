// Hook de mutation login — appel API, mise à jour du store, parsing des erreurs
import { useMutation } from '@tanstack/react-query';
import useAuthStore from '@/store/authStore';
import { login } from '@/api/auth';

/**
 * Parse les erreurs d'authentification Axios/Django en message lisible en français.
 * @param {Object} error - Objet erreur Axios
 * @returns {string}
 */
export function parseLoginError(error) {
  if (error?.response?.status === 429) {
    return "Trop de tentatives de connexion. Patientez une minute avant de réessayer.";
  }

  // simplejwt répond 401 (« No active account found… », en anglais) pour un
  // identifiant inconnu, un mot de passe faux ou un compte désactivé
  //.
  // Profil suspendu : 401 avec le motif dans `detail`, affiché tel quel.
  if (error?.response?.status === 401) {
    return error.response.data?.code === 'profil_suspendu' && error.response.data.detail
      ? error.response.data.detail
      : "Identifiant ou mot de passe incorrect.";
  }

  // Page d'erreur du serveur (HTML) : jamais affichée telle quelle.
  if (error?.response?.status >= 500) {
    return "Le serveur a rencontré une erreur. Réessayez plus tard.";
  }

  if (error?.response?.data) {
    const { non_field_errors, detail } = error.response.data;

    if (Array.isArray(non_field_errors) && non_field_errors.length > 0) {
      return non_field_errors[0];
    }
    if (detail) {
      return detail;
    }
  }

  if (error?.request) {
    return "Impossible de joindre le serveur. Veuillez vérifier votre connexion.";
  }

  return "Une erreur inattendue est survenue lors de la connexion.";
}

/**
 * Hook de mutation pour le login.
 * Met à jour authStore via getState() — pas d'abonnement réactif dans onSuccess.
 * La navigation est gérée côté composant via la réactivité de isAuthenticated.
 * @returns {import('@tanstack/react-query').UseMutationResult}
 */
export function useLogin() {
  return useMutation({
    mutationFn: ({ username, password }) => login(username, password),

    onSuccess: ({ access, refresh, user }) => {
      // Nettoyage préventif du store avant d'écrire les nouvelles données
      // pour éviter qu'un ancien rôle en cache ne persiste
      useAuthStore.getState().clearAuth();
      useAuthStore.getState().setAuth({
        accessToken:  access,
        refreshToken: refresh,
        user,
      });
    },
  });
}