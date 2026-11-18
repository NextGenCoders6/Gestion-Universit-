import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuthStore from '@/store/authStore';
import * as api from '../api';
import Transports from './Transports';

vi.mock('../api');

describe('Finance — transports', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.listerTransports.mockResolvedValue({ count: 0, results: [] });
    api.listerBusFinance.mockResolvedValue([{ id: 1, numero: '01', plaque: 'CG-001-AA' }]);
    api.creerDepense.mockResolvedValue({ id: 3, numero: 'OP-2026-000010', montant: 45000 });
  });

  it('saisie d’une dépense de carburant', async () => {
    useAuthStore.getState().setAuth({ accessToken: 'a', refreshToken: 'r',
      user: { id: 1, username: 'u', nom_complet: 'U', roles: [], modules: [{ code: 'finance', niveaux: ['responsable'] }] } });
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MemoryRouter><Transports /></MemoryRouter></QueryClientProvider>);
    await user.click(await screen.findByRole('button', { name: /Nouvelle dépense/ }));
    const dialog = within(screen.getByRole('dialog'));
    await user.selectOptions(dialog.getByLabelText(/^Bus/), '1');
    await user.selectOptions(dialog.getByLabelText(/^Type/), 'carburant');
    await user.type(dialog.getByLabelText(/^Montant/), '45000');
    await user.click(dialog.getByRole('button', { name: 'Enregistrer' }));
    await waitFor(() => expect(api.creerDepense).toHaveBeenCalledWith(expect.objectContaining({ bus: 1, type: 'carburant', montant: '45000' })));
  });
});
