/** Chiffres des tuiles du launchpad : un résumé par module accessible (GET /api/core/lanceur/). */
import apiClient from '@/api/client';

export const lireLanceur = () => apiClient.get('/core/lanceur/').then((r) => r.data);
