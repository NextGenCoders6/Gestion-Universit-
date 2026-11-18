import { useQuery } from '@tanstack/react-query';
import useAuthStore, { aDroit } from '@/store/authStore';
import * as api from './api';

/** Vrai pour un responsable de l'EDT ou un gestionnaire de périmètre (chef, référent). */
export function usePeutGerer() {
  return useAuthStore((s) => aDroit(s, 'edt', 'responsable') || aDroit(s, 'edt', 'perimetre'));
}

export function useAnnee() {
  return useQuery({ queryKey: ['edt', 'annee'], queryFn: api.anneeEnCours, staleTime: Infinity });
}

export function useEnseignements(params = {}) {
  return useQuery({ queryKey: ['edt', 'enseignements', params], queryFn: () => api.listerEnseignements(params) });
}

export function useEnseignants() {
  return useQuery({ queryKey: ['edt', 'enseignants'], queryFn: api.listerEnseignants, staleTime: 5 * 60 * 1000 });
}

export function useSeances(params, options = {}) {
  return useQuery({ queryKey: ['edt', 'seances', params], queryFn: () => api.listerSeances(params), ...options });
}

/** Classes et EC du périmètre, tirés des lignes « enseignements » (une par EC × classe). */
export function classesEtEcs(lignes = []) {
  const classes = new Map();
  for (const l of lignes) {
    if (!classes.has(l.classe)) classes.set(l.classe, { id: l.classe, libelle: l.classe_libelle, ecs: [] });
    classes.get(l.classe).ecs.push({ id: l.ec, code: l.ec_code, libelle: l.ec_libelle, semestre: l.semestre });
  }
  return [...classes.values()];
}
