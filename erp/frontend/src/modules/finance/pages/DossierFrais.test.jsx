import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuthStore from '@/store/authStore';
import * as api from '../api';
import DossierFrais from './DossierFrais';

vi.mock('../api');

const DOSSIER = { id: 7, matricule: 'UCCB26ALPGR00001', nom_complet: 'ALPHA Grâce', classe_libelle: 'L1 MIP — 2026-2027',
  annee_libelle: '2026-2027', montant_du: 1500000, montant_paye: 75000, reste: 1425000, trop_percu: 0, statut: 'partiel',
  montant_ajuste: false, echeancier_adapte: false, sans_tarif: false, en_retard: true, montant_en_retard: 75000,
  prochaine_echeance: { numero: 1, mois: '2026-10', date_limite: '2026-11-05', montant: 150000, paye: 75000, etat: 'en_retard' },
  echeances: [
    { numero: 1, mois: '2026-10', date_limite: '2026-11-05', montant: 150000, paye: 75000, etat: 'en_retard' },
    { numero: 2, mois: '2026-11', date_limite: '2026-12-05', montant: 150000, paye: 0, etat: 'a_venir' },
  ],
  paiements: [{ id: 3, date: '2026-10-12', montant: 75000, mode: 'especes', mode_libelle: 'Espèces', reference: '',
    numero: 'OP-2026-000001', annule: false, motif_annulation: '', par: 'caisse' }] };

function rendre(niveaux) {
  useAuthStore.getState().setAuth({ accessToken: 'a', refreshToken: 'r',
    user: { id: 1, username: 'u', nom_complet: 'U', roles: [], modules: [{ code: 'finance', niveaux }] } });
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter initialEntries={['/finance/frais/7']}>
    <Routes><Route path="/finance/frais/:id" element={<DossierFrais />} /></Routes></MemoryRouter></QueryClientProvider>);
}

describe('Finance — dossier de frais', () => {
  beforeEach(() => { vi.resetAllMocks(); api.dossierFrais.mockResolvedValue(DOSSIER); });

  it('échéancier : mensualité en retard signalée', async () => {
    rendre(['utilisateur']);
    const ligne = await screen.findByRole('row', { name: /2026-10/ });
    expect(within(ligne).getByText('En retard')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Ajuster/ })).not.toBeInTheDocument();
  });

  it('paiement au-delà du reste : message du serveur', async () => {
    api.encaisser.mockRejectedValue({ response: { status: 400, data: { montant: ['Le montant dépasse le reste dû (1425000 FCFA).'] } } });
    const user = userEvent.setup();
    rendre(['utilisateur']);
    await user.click(await screen.findByRole('button', { name: /Encaisser/ }));
    const dialog = within(screen.getByRole('dialog'));
    await user.type(dialog.getByLabelText(/^Montant/), '2000000');
    await user.selectOptions(dialog.getByLabelText(/^Mode/), 'especes');
    await user.click(dialog.getByRole('button', { name: 'Encaisser' }));
    await waitFor(() => expect(api.encaisser).toHaveBeenCalledWith(7, expect.objectContaining({ montant: '2000000', mode: 'especes' })));
    expect(await dialog.findByText('Le montant dépasse le reste dû (1425000 FCFA).')).toBeInTheDocument();
  });
});
