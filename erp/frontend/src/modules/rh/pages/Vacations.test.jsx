import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../api';
import Vacations from './Vacations';

vi.mock('../api');

const LIGNE = { affectation: 4, ec_code: 'ARCHI1', ec_libelle: 'Architecture', classe_libelle: 'L1 MIP — 2026-2027',
  enseignant_nom: 'MBEMBA Christelle', type_seance: null, heures_prevues: 6, heures_effectuees: 6, heures_jumelles: 0,
  heures_dues: 6, terminee: true, confirmable: true, motif_blocage: null, taux_horaire: 6000, vacation: null };

describe('RH — vacations', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.listerVacations.mockResolvedValue([LIGNE]);
    api.historiqueVacations.mockResolvedValue([]);
  });

  it('filtre par état', async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MemoryRouter><Vacations /></MemoryRouter></QueryClientProvider>);
    expect(await screen.findByText('MBEMBA Christelle')).toBeInTheDocument();
    expect(api.listerVacations).toHaveBeenLastCalledWith({ etat: 'a_confirmer' });
    await user.click(screen.getByRole('tab', { name: 'Confirmées' }));
    await waitFor(() => expect(api.listerVacations).toHaveBeenLastCalledWith({ etat: 'confirmee' }));
  });
});
