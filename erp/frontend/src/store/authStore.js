import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/**
 * Session de l'utilisateur. `user` a la forme renvoyée par /api/core/moi/ :
 * { id, username, nom_complet, photo, personne_id,
 *   modules: [{ code, libelle, niveaux }], roles: [string], faculte_rattachee }
 */
const useAuthStore = create(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      // Vrai après « Déconnexion » : le login ne renvoie pas le compte suivant
      // vers la dernière page du compte précédent.
      deconnexionVolontaire: false,

      setAuth: ({ accessToken, refreshToken, user }) => set({
        accessToken,
        refreshToken,
        user,
        isAuthenticated: true,
        deconnexionVolontaire: false,
      }),

      // Le serveur fait tourner le refresh token à chaque renouvellement et
      // blackliste l'ancien : il faut garder le nouveau.
      setTokens: ({ accessToken, refreshToken }) => set((state) => ({
        accessToken,
        refreshToken: refreshToken ?? state.refreshToken,
      })),

      setUser: (user) => set({ user }),

      clearAuth: ({ volontaire = false } = {}) => set({
        accessToken: null,
        refreshToken: null,
        user: null,
        isAuthenticated: false,
        deconnexionVolontaire: volontaire,
      }),
    }),
    {
      name: 'erp-auth',
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
      }),
      merge: (persistedState, currentState) => ({
        ...currentState,
        ...persistedState,
        isAuthenticated: !!persistedState?.accessToken,
      }),
    },
  ),
);

export const selectModules = (state) => state.user?.modules ?? [];

export const niveauxModule = (state, module) =>
  selectModules(state).find((m) => m.code === module)?.niveaux ?? [];

export const aDroit = (state, module, niveau) => {
  const niveaux = niveauxModule(state, module);
  return niveau ? niveaux.includes(niveau) : niveaux.length > 0;
};

export const aRole = (state, role) => (state.user?.roles ?? []).includes(role);

export default useAuthStore;
