import { useQuery } from '@tanstack/react-query';
import useAuthStore, { aDroit } from '@/store/authStore';
import * as api from './api';

export const useEstResponsableRH = () => useAuthStore((s) => aDroit(s, 'rh', 'responsable'));

export function useDepartements() {
  return useQuery({ queryKey: ['rh', 'departements'], queryFn: api.listerDepartements, staleTime: 5 * 60 * 1000 });
}

export function useFacultes() {
  return useQuery({ queryKey: ['rh', 'facultes'], queryFn: api.listerFacultes, staleTime: 5 * 60 * 1000 });
}
