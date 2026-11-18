import { render, screen, waitFor, within } from '@testing-library/react';
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

function rendre() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter><Vacations /></MemoryRouter></QueryClientProvider>);
}

describe('Scolarité — vacations', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.listerVacations.mockResolvedValue([LIGNE]);
    api.historiqueVacations.mockResolvedValue([]);
    api.listerAnnees.mockResolvedValue([]);
  });

  it('motif exigé quand les heures retenues changent', async () => {
    api.confirmerVacation.mockResolvedValue({ ...LIGNE, vacation: { heures_retenues: 5, montant: 30000, taux_horaire: 6000, motif: 'x' } });
    const user = userEvent.setup();
    rendre();
    await user.click(await screen.findByRole('button', { name: /Confirmer/ }));
    const dialog = within(screen.getByRole('dialog'));
    const champ = dialog.getByLabelText(/Heures retenues/);
    expect(champ).toHaveValue(6);
    await user.clear(champ);
    await user.type(champ, '5');
    await user.click(dialog.getByRole('button', { name: 'Confirmer la vacation' }));
    expect(await dialog.findByText(/Indiquez le motif/)).toBeInTheDocument();
    expect(api.confirmerVacation).not.toHaveBeenCalled();
    await user.type(dialog.getByLabelText(/Motif/), 'Séance écourtée');
    await user.click(dialog.getByRole('button', { name: 'Confirmer la vacation' }));
    await waitFor(() => expect(api.confirmerVacation).toHaveBeenCalledWith(4, { heures_retenues: '5', motif: 'Séance écourtée' }));
  });

  it('retrait avec motif', async () => {
    api.listerVacations.mockResolvedValue([{ ...LIGNE, confirmable: false, motif_blocage: 'Vacation déjà confirmée.',
      vacation: { heures_retenues: 6, montant: 36000, taux_horaire: 6000, motif: '' } }]);
    api.retirerVacation.mockResolvedValue({ ...LIGNE, vacation: null });
    const user = userEvent.setup();
    rendre();
    await user.click(screen.getByRole('tab', { name: 'Confirmées' }));
    await user.click(await screen.findByRole('button', { name: /Retirer/ }));
    const dialog = within(screen.getByRole('dialog'));
    await user.type(dialog.getByLabelText(/Motif/), 'Erreur de classe');
    await user.click(dialog.getByRole('button', { name: 'Retirer la confirmation' }));
    await waitFor(() => expect(api.retirerVacation).toHaveBeenCalledWith(4, 'Erreur de classe'));
  });
});
