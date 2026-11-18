import { QueryClient } from '@tanstack/react-query';
import { estDelaiDepasse } from '@/api/client';

/** Cache des données serveur, partagé par l'application (vidé à la déconnexion). */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      // Un nouvel essai, sauf après un délai dépassé : un serveur muet
      // pendant 30 s ne répondra pas mieux.
      retry: (echecs, erreur) => echecs < 1 && !estDelaiDepasse(erreur),
      refetchOnWindowFocus: false,
    },
  },
});
