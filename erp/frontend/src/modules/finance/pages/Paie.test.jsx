import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuthStore from '@/store/authStore';
import * as api from '../api';
import Paie from './Paie';

vi.mock('../api');

const LIGNE = { id: 4, origine: 'salaire', mois: '2026-10', personne: 2, nom_complet: 'BOUANGA Marc', role: 'employe',
  libelle: 'Salaire 2026-10 — BOUANGA Marc', contrat: 1, montant_du: 120000, montant_paye: 0, reste: 120000,
  statut: 'en_attente', montant_ajuste: false };

function rendre(niveaux) {
  useAuthStore.getState().setAuth({ accessToken: 'a', refreshToken: 'r',
    user: { id: 1, username: 'u', nom_complet: 'U', roles: [], modules: [{ code: 'finance', niveaux }] } });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter><Paie role="employe" titre="Paie du personnel" /></MemoryRouter></QueryClientProvider>);
}

describe('Finance — paie', () => {
  beforeEach(() => { vi.resetAllMocks(); api.listerPaie.mockResolvedValue({ count: 1, results: [LIGNE] }); });

  it('lecture seule pour finance_utilisateur', async () => {
    rendre(['utilisateur']);
    expect(await screen.findByText('BOUANGA Marc')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Générer/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Payer/ })).not.toBeInTheDocument();
  });

  it('génère la paie du mois choisi', async () => {
    api.genererPaie.mockResolvedValue({ mois: '2026-10', creees: 3, existantes: 0 });
    const user = userEvent.setup();
    rendre(['responsable']);
    await screen.findByText('BOUANGA Marc');
    const mois = screen.getByLabelText('Mois');
    await user.clear(mois);
    await user.type(mois, '2026-10');
    await user.click(screen.getByRole('button', { name: /Générer la paie/ }));
    await waitFor(() => expect(api.genererPaie).toHaveBeenCalledWith('2026-10'));
  });

  it('liste du mois courant avec toutes les vacations', async () => {
    rendre(['utilisateur']);
    await screen.findByText('BOUANGA Marc');
    const mois = new Date().toISOString().slice(0, 7);
    expect(api.listerPaie).toHaveBeenLastCalledWith(expect.objectContaining({ role: 'employe', mois, avec_vacations: 'true' }));
  });
});
