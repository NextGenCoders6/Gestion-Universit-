/** Appels à l'API Paramètres (/api/core/…). */
import apiClient, { fetchAllPages } from '@/api/client';

export const lister = (ressource, params = {}) => fetchAllPages(`/core/${ressource}/`, params);
export const creer = (ressource, donnees) => apiClient.post(`/core/${ressource}/`, donnees).then((r) => r.data);
export const modifier = (ressource, id, donnees) =>
  apiClient.patch(`/core/${ressource}/${id}/`, donnees).then((r) => r.data);
export const supprimer = (ressource, id) => apiClient.delete(`/core/${ressource}/${id}/`);
export const agir = (ressource, id, action, donnees = {}) =>
  apiClient.post(`/core/${ressource}/${id}/${action}/`, donnees).then((r) => r.data);

export const listerModules = () => apiClient.get('/core/modules/').then((r) => r.data);
export const listerUtilisateurs = (params = {}) => fetchAllPages('/core/utilisateurs/', params);
export const creerUtilisateur = (donnees) => apiClient.post('/core/utilisateurs/', donnees).then((r) => r.data);
export const modifierUtilisateur = (id, donnees) =>
  apiClient.patch(`/core/utilisateurs/${id}/`, donnees).then((r) => r.data);
export const changerMotDePasse = (id, password) =>
  apiClient.post(`/core/utilisateurs/${id}/mot_de_passe/`, { password }).then((r) => r.data);

export const lireEtablissement = () => apiClient.get('/core/etablissement/').then((r) => r.data);
export const modifierEtablissement = (donnees) => apiClient.put('/core/etablissement/', donnees).then((r) => r.data);

/** Journal d'audit, paginé côté serveur : renvoie { count, results }. */
export const listerAudit = (params = {}) => apiClient.get('/core/audit/', { params }).then((r) => r.data);
