import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import useAuthStore, { aDroit } from '@/store/authStore';
import * as api from './api';

export const useEstSecretariat = () => useAuthStore((s) => aDroit(s, 'scolarite', 'secretariat'));
export const useEstFaculte = () => useAuthStore((s) => aDroit(s, 'scolarite', 'faculte'));

export function useClasses() {
  return useQuery({ queryKey: ['scolarite', 'classes'], queryFn: () => api.listerClasses(), staleTime: 5 * 60 * 1000 });
}

/** Sélection gardée dans l'adresse (?classe=…&semestre=…) : on peut recharger ou partager la page. */
export function useSelection(cles) {
  const [params, setParams] = useSearchParams();
  const valeurs = Object.fromEntries(cles.map((c) => [c, params.get(c) ?? '']));
  const changer = (modif) => {
    const suivant = new URLSearchParams(params);
    for (const [cle, valeur] of Object.entries(modif)) {
      if (valeur) suivant.set(cle, valeur); else suivant.delete(cle);
    }
    setParams(suivant, { replace: true });
  };
  return [valeurs, changer];
}
