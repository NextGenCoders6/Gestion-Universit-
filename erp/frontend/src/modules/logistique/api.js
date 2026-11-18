/** Appels à l'API Logistique (/api/logistique/…). */
import apiClient, { fetchAllPages } from '@/api/client';

const donnees = (r) => r.data;

export const tableauDeBord = () => apiClient.get('/logistique/tableau-de-bord/').then(donnees);
export const listerBus = () => fetchAllPages('/logistique/bus/');
export const creerBus = (d) => apiClient.post('/logistique/bus/', d).then(donnees);
export const modifierBus = (id, d) => apiClient.patch(`/logistique/bus/${id}/`, d).then(donnees);
export const supprimerBus = (id) => apiClient.delete(`/logistique/bus/${id}/`);
export const changerStatut = (id, statut) => apiClient.post(`/logistique/bus/${id}/statut/`, { statut }).then(donnees);
export const listerTrajets = () => fetchAllPages('/logistique/trajets/');
export const creerTrajet = (d) => apiClient.post('/logistique/trajets/', d).then(donnees);
export const modifierTrajet = (id, d) => apiClient.patch(`/logistique/trajets/${id}/`, d).then(donnees);
export const supprimerTrajet = (id) => apiClient.delete(`/logistique/trajets/${id}/`);
export const listerAffectations = (params = {}) => apiClient.get('/logistique/affectations/', { params }).then(donnees);
export const creerAffectation = (d) => apiClient.post('/logistique/affectations/', d).then(donnees);
export const annulerAffectation = (id) => apiClient.post(`/logistique/affectations/${id}/annuler/`);
export const terminerAffectation = (id, dateFin) => apiClient.post(`/logistique/affectations/${id}/terminer/`, { date_fin: dateFin }).then(donnees);
export const chauffeursDisponibles = (date) => apiClient.get('/logistique/chauffeurs/', { params: date ? { date } : {} }).then(donnees);
export const couts = (params = {}) => apiClient.get('/logistique/couts/', { params }).then(donnees);
