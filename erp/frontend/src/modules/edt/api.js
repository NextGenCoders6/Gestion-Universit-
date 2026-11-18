/** Appels à l'API du module Emploi du temps (/api/edt/…). */
import apiClient, { fetchAllPages } from '@/api/client';

const donnees = (r) => r.data;

export const listerSeances = (params = {}) => fetchAllPages('/edt/seances/', { page_size: 200, ...params });
export const creerSeance = (d) => apiClient.post('/edt/seances/', d).then(donnees);
export const modifierSeance = (id, d) => apiClient.patch(`/edt/seances/${id}/`, d).then(donnees);
export const supprimerSeance = (id) => apiClient.delete(`/edt/seances/${id}/`);
export const publierSeance = (id) => apiClient.post(`/edt/seances/${id}/publier/`).then(donnees);
export const depublierSeance = (id) => apiClient.post(`/edt/seances/${id}/depublier/`).then(donnees);
export const publierEnMasse = (ids) => apiClient.post('/edt/seances/publier_masse/', { seance_ids: ids }).then(donnees);
export const reporterSeance = (id, d) => apiClient.patch(`/edt/seances/${id}/reporter/`, d).then(donnees);
export const listerConflits = (params = {}) => apiClient.get('/edt/seances/conflits/', { params }).then(donnees);

export const listerEnseignements = (params = {}) => apiClient.get('/edt/enseignements/', { params }).then(donnees);
export const listerEnseignants = () => fetchAllPages('/edt/enseignants/', { page_size: 200 });
export const creerAffectation = (d) => apiClient.post('/edt/affectations/', d).then(donnees);
export const modifierAffectation = (id, d) => apiClient.patch(`/edt/affectations/${id}/`, d).then(donnees);
export const supprimerAffectation = (id) => apiClient.delete(`/edt/affectations/${id}/`);

export const listerReferents = () => fetchAllPages('/edt/referents/');
export const creerReferent = (d) => apiClient.post('/edt/referents/', d).then(donnees);
export const modifierReferent = (id, d) => apiClient.patch(`/edt/referents/${id}/`, d).then(donnees);
export const supprimerReferent = (id) => apiClient.delete(`/edt/referents/${id}/`);

export const listerClasses = (params = {}) => fetchAllPages('/core/classes/', params);
export const anneeEnCours = () => fetchAllPages('/core/annees/').then((a) => a.find((x) => x.en_cours) ?? a[0] ?? null);
