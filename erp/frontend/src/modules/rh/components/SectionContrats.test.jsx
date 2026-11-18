import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuthStore from '@/store/authStore';
import * as api from '../api';
import SectionContrats from './SectionContrats';

vi.mock('../api');
vi.mock('@/lib/confirmer', () => ({ confirmer: () => Promise.resolve(true) }));

describe('RH — contrats', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    useAuthStore.getState().setAuth({ accessToken: 'a', refreshToken: 'r',
      user: { id: 1, username: 'u', nom_complet: 'U', roles: [], modules: [{ code: 'rh', niveaux: ['responsable'] }] } });
  });

  it('annule un contrat à venir', async () => {
    api.supprimerContrat.mockResolvedValue({});
    const client = new QueryClient();
    render(<QueryClientProvider client={client}><SectionContrats personne={3} enseignant contrats={[
      { id: 8, type: 'permanent', date_debut: '2027-01-01', date_fin: null, salaire_mensuel: 500000, rib: '', numero_secu: '', diplome: '', etat: 'a_venir' }]} /></QueryClientProvider>);
    screen.getByRole('button', { name: 'Annuler le contrat' }).click();
    await waitFor(() => expect(api.supprimerContrat).toHaveBeenCalledWith(8));
  });
});
