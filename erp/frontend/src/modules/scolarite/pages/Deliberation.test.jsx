import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import * as api from '../api';
import Deliberation from './Deliberation';

vi.mock('../api');

const CLASSES = [{ id: 1, libelle: 'L1 MIP — 2026-2027', niveau: 'L1', semestres: ['S1', 'S2'], archivee: false, ecs: [] }];
const LIGNE = { inscription: 1, etudiant: 1, matricule: 'M1', nom_complet: 'BETA Paul', moyenne: 9, eliminatoire: false,
  decision: 'AJOURNÉ', mention: 'NÉANT', credits_valides: 0, credits_totaux: 9, ecs_non_saisis: ['ANA1', 'PHYS1'], rang: 1,
  ues: [{ id: 3, code: 'UE-1', libelle: 'UE 1', moyenne_ue: 9, credits_ue: 4, credits_ue_total: 9, validee: true, ecs: [] }] };

describe('Scolarité — délibération', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    api.listerClasses.mockResolvedValue(CLASSES);
    api.deliberation.mockResolvedValue({ classe: 1, classe_libelle: 'L1 MIP — 2026-2027', semestre: 'S1', archivee: false,
      ues: [{ id: 3, code: 'UE-1', libelle: 'UE 1', ecs: [] }], lignes: [LIGNE], ecs_non_saisis: 2, deliberee: false, delibere_le: null });
  });

  it('alerte quand des notes manquent', async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/scolarite/deliberation?classe=1&semestre=S1']}><Deliberation /></MemoryRouter>
    </QueryClientProvider>);
    expect(await screen.findByText(/2 notes non saisies/)).toBeInTheDocument();
    expect(screen.getByText('BETA Paul')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Enregistrer la délibération/ })).toBeInTheDocument();
  });
});
