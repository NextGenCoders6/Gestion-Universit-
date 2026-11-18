import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../api';
import SaisieNotes from './SaisieNotes';

vi.mock('../api');

const CLASSES = [{ id: 1, libelle: 'L1 MIP — 2026-2027', niveau: 'L1', semestres: ['S1', 'S2'], archivee: false,
  ecs: [{ id: 5, code: 'ALGO', libelle: 'Algorithmique', semestre: 'S1', credits: 4 }] }];
const GRILLE = { classe: 1, ec: { id: 5, code: 'ALGO', libelle: 'Algorithmique', credits: 4 }, archivee: false, lignes: [
  { note_id: 11, etudiant: 1, matricule: 'UCCB26ALPGR00001', nom_complet: 'ALPHA Grâce', devoir: null, session: null, sr: null, absent: false, moyenne: null },
  { note_id: 12, etudiant: 2, matricule: 'UCCB26BETPA00002', nom_complet: 'BETA Paul', devoir: null, session: null, sr: null, absent: false, moyenne: null },
] };

function rendre() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/scolarite/saisie?classe=1&ec=5']}><SaisieNotes /></MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Scolarité — saisie des notes', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.listerClasses.mockResolvedValue(CLASSES);
    api.grilleSaisie.mockResolvedValue(GRILLE);
  });

  it("signale la cellule en erreur et garde la saisie des autres", async () => {
    api.enregistrerSaisie.mockResolvedValue({ enregistrees: 1, erreurs: { 12: { devoir: 'Une note est comprise entre 0 et 20.' } } });
    const user = userEvent.setup();
    rendre();
    const alpha = within(await screen.findByRole('row', { name: /ALPHA Grâce/ }));
    const beta = within(screen.getByRole('row', { name: /BETA Paul/ }));
    await user.type(alpha.getByRole('textbox', { name: 'Devoir — ALPHA Grâce' }), '12');
    await user.type(alpha.getByRole('textbox', { name: 'Session — ALPHA Grâce' }), '14');
    await user.type(beta.getByRole('textbox', { name: 'Devoir — BETA Paul' }), '21');
    await user.click(screen.getByRole('button', { name: /Enregistrer/ }));
    await waitFor(() => expect(api.enregistrerSaisie).toHaveBeenCalledWith([
      { note_id: 11, devoir: '12', session: '14', sr: null, absent: false },
      { note_id: 12, devoir: '21', session: null, sr: null, absent: false },
    ]));
    expect(await beta.findByText('Une note est comprise entre 0 et 20.')).toBeInTheDocument();
    expect(beta.getByRole('textbox', { name: 'Devoir — BETA Paul' })).toHaveValue('21');
    expect(beta.getByRole('textbox', { name: 'Devoir — BETA Paul' })).toHaveAttribute('aria-invalid', 'true');
  });

  it('semestre délibéré : grille en lecture seule', async () => {
    api.grilleSaisie.mockResolvedValue({ ...GRILLE, deliberee: true });
    rendre();
    expect(await screen.findByText(/déjà délibéré/)).toBeInTheDocument();
    expect(screen.getByRole('textbox', { name: 'Devoir — ALPHA Grâce' })).toBeDisabled();
  });
});
