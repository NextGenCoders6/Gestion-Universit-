import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuthStore from '@/store/authStore';
import * as api from '../api';
import Affectations from './Affectations';
import Bus from './Bus';

vi.mock('../api');

const BUS = [{ id: 1, numero: '01', plaque: 'CG-001-AA', capacite: 50, statut: 'actif',
  affectation_active: { id: 4, chauffeur: 'NZABA Didier', trajet: 'Ligne A' } }];

function rendre(element, niveaux) {
  useAuthStore.getState().setAuth({ accessToken: 'a', refreshToken: 'r',
    user: { id: 1, username: 'u', nom_complet: 'U', roles: [], modules: [{ code: 'logistique', niveaux }] } });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter>{element}</MemoryRouter></QueryClientProvider>);
}

describe('Logistique', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.listerBus.mockResolvedValue(BUS);
    api.listerTrajets.mockResolvedValue([{ id: 2, nom: 'Ligne A', depart: 'Centre', destination: 'Campus', heure_depart: '06:30:00', heure_arrivee: '07:30:00' }]);
    api.listerAffectations.mockResolvedValue({ count: 0, results: [] });
    api.chauffeursDisponibles.mockResolvedValue([{ id: 7, matricule: 'UCCB-PERS-00007', nom_complet: 'MALONGA Jean' }]);
  });

  it('lecture seule pour logistique_utilisateur', async () => {
    rendre(<Bus />, ['utilisateur']);
    expect(await screen.findByText(/CG-001-AA/)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Nouveau bus/ })).not.toBeInTheDocument();
  });

  it('avertit avant de mettre en maintenance un bus affecté', async () => {
    const user = userEvent.setup();
    rendre(<Bus />, ['responsable']);
    await user.click(await screen.findByRole('button', { name: /Statut du bus 01/ }));
    const dialog = within(screen.getByRole('dialog'));
    await user.selectOptions(dialog.getByLabelText(/^Statut/), 'maintenance');
    expect(dialog.getByText(/NZABA Didier.*sera terminée/)).toBeInTheDocument();
  });

  it('nouvelle affectation : message du serveur', async () => {
    api.creerAffectation.mockRejectedValue({ response: { status: 400, data: { chauffeur: ['Ce chauffeur conduit déjà un bus sur cette période.'] } } });
    const user = userEvent.setup();
    rendre(<Affectations />, ['responsable']);
    await user.click(await screen.findByRole('button', { name: /Nouvelle affectation/ }));
    const dialog = within(screen.getByRole('dialog'));
    await user.selectOptions(dialog.getByLabelText(/^Bus/), '1');
    await user.selectOptions(dialog.getByLabelText(/^Chauffeur/), '7');
    await user.selectOptions(dialog.getByLabelText(/^Trajet/), '2');
    await user.click(dialog.getByRole('button', { name: 'Enregistrer' }));
    await waitFor(() => expect(api.creerAffectation).toHaveBeenCalled());
    expect(await dialog.findByText('Ce chauffeur conduit déjà un bus sur cette période.')).toBeInTheDocument();
  });
});
