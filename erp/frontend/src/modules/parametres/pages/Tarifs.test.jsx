import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as finance from '@/modules/finance/api';
import Tarifs from './Tarifs';

vi.mock('@/modules/finance/api');

describe('Paramètres — tarifs', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    finance.listerTarifs.mockResolvedValue([]);
    finance.listerAnnees.mockResolvedValue([{ id: 1, libelle: '2026-2027', en_cours: true, date_debut: '2026-10-01' }]);
    finance.listerParcours.mockResolvedValue([{ id: 1, code: 'L1', type_parcours: 'Licence' }]);
  });

  it("aperçu de l'échéancier", async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MemoryRouter><Tarifs /></MemoryRouter></QueryClientProvider>);
    await user.click(await screen.findByRole('button', { name: /Nouveau tarif/ }));
    const dialog = within(screen.getByRole('dialog'));
    await user.selectOptions(dialog.getByLabelText(/^Année/), '1');
    await user.type(dialog.getByLabelText(/^Montant de l’année/), '1500000');
    expect(await dialog.findByText(/10 mensualités de 150\s000 FCFA/)).toBeInTheDocument();
    expect(dialog.getByText(/05\/11\/2026/)).toBeInTheDocument();
  });
});
