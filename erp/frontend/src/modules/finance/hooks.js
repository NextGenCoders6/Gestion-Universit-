import useAuthStore, { aDroit } from '@/store/authStore';

export const useEstResponsableFinance = () => useAuthStore((s) => aDroit(s, 'finance', 'responsable'));
