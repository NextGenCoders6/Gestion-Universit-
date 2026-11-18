import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../api';
import Classes from './Classes';

vi.mock('../api');

const DONNEES = {
  annees: [{ id: 1, libelle: '2026-2027' }],
  parcours: [{ id: 1, code: 'L1' }, { id: 2, code: 'L2' }],
  portails: [{ id: 1, code: 'MIP', faculte_code: 'FST' }],
  filieres: [{ id: 4, code: 'INFO', faculte_code: 'FST' }],
  classes: [{ id: 9, libelle: 'L1 MIP — 2026-2027', parcours_code: 'L1', annee_libelle: '2026-2027' }],
};

function rendre() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter><Classes /></MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Paramètres — Classes', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.lister.mockImplementation((ressource) => Promise.resolve(DONNEES[ressource] ?? []));
  });

  it('liste les classes', async () => {
    rendre();
    expect(await screen.findByText('L1 MIP — 2026-2027')).toBeInTheDocument();
  });

  it('affiche l’erreur de champ du serveur sous le champ Filière', async () => {
    api.creer.mockRejectedValue({
      response: { status: 400, data: { filiere: ['Une classe de L1 est rattachée à un portail, pas à une filière.'] } },
    });
    const user = userEvent.setup();
    rendre();
    await user.click(await screen.findByRole('button', { name: /Nouvelle classe/ }));
    const dialog = await screen.findByRole('dialog');
    await user.selectOptions(within(dialog).getByLabelText('Année'), '1');
    await user.selectOptions(within(dialog).getByLabelText('Niveau'), '1');
    await user.selectOptions(within(dialog).getByLabelText('Filière'), '4');
    await user.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));

    await waitFor(() => expect(api.creer).toHaveBeenCalledWith('classes', { annee: 1, parcours: 1, portail: null, filiere: 4 }));
    const message = await within(dialog).findByText(/rattachée à un portail, pas à une filière/);
    expect(message.closest('[data-champ]')).toHaveAttribute('data-champ', 'filiere');
  });
});
