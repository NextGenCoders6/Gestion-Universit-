import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import useAuthStore from '@/store/authStore';
import * as api from '../api';
import AccueilEnseignant from './AccueilEnseignant';

vi.mock('../api', () => ({ monPlanning: vi.fn(), mesEnseignements: vi.fn(), mesDocuments: vi.fn() }));

const seance = (jour, debut, fin) => ({
  id: `${jour}${debut}`, ec_code: 'ALGO1', ec_libelle: 'Algorithmique 1', classe_libelle: 'L1 MIP — 2026-2027',
  creneau_effectif: { jour, debut, fin },
});
const AFFECTATIONS = [
  { id: 1, classe: 1, ec_code: 'ALGO1', ec_libelle: 'Algorithmique 1', heures_effectuees: 6, heures_consommees: 12, heures_prevues: 24 },
  { id: 2, classe: 1, ec_code: 'ARCHI1', ec_libelle: 'Architecture', heures_effectuees: 12, heures_consommees: 12, heures_prevues: 48 },
  { id: 3, classe: 3, ec_code: 'WEB1', ec_libelle: 'Développement web', heures_effectuees: 4, heures_consommees: 4, heures_prevues: 4 },
];

function rendre() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter><AccueilEnseignant /></MemoryRouter></QueryClientProvider>);
}

describe('Accueil enseignant', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 10, 19, 19, 0));
    useAuthStore.getState().setAuth({ accessToken: 'a', refreshToken: 'r',
      user: { id: 2, username: 'enseignant', nom_complet: 'MBEMBA Christelle', roles: ['enseignant'], modules: [] } });
    api.monPlanning.mockResolvedValue([seance('2026-11-20', '09:00', '11:00'), seance('2026-11-21', '09:00', '10:30')]);
    api.mesEnseignements.mockResolvedValue(AFFECTATIONS);
    api.mesDocuments.mockResolvedValue([]);
  });
  afterEach(() => { vi.useRealTimers(); vi.clearAllMocks(); });

  it('résume séances, heures, classes et documents', async () => {
    rendre();
    expect(screen.getByRole('heading', { name: 'Bonsoir, MBEMBA Christelle' })).toBeInTheDocument();
    expect(await screen.findByText('3,5 h')).toBeInTheDocument();
    expect(await screen.findByText('22 h / 76 h')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(await screen.findByText('0')).toBeInTheDocument();
    expect(screen.getAllByText('L1 MIP — 2026-2027')).toHaveLength(2);
    expect(screen.getAllByRole('progressbar')).toHaveLength(3);
    expect(screen.getByRole('link', { name: /Prochaines séances/ })).toHaveAttribute('href', '/moi/planning');
    expect(screen.getByRole('link', { name: /Avancement/ })).toHaveAttribute('href', '/moi/enseignements');
    expect(api.monPlanning).toHaveBeenCalledWith({ date_debut: '2026-11-16', date_fin: '2026-11-22' });
    expect(api.monPlanning).toHaveBeenCalledWith({ date_debut: '2026-11-19', date_fin: '2026-12-03' });
  });

  it('aucune séance à venir, aucune affectation', async () => {
    api.monPlanning.mockResolvedValue([]);
    api.mesEnseignements.mockResolvedValue([]);
    rendre();
    expect(await screen.findByText('Aucune séance dans les 14 prochains jours.')).toBeInTheDocument();
    expect(await screen.findByText('Aucune affectation pour l’instant.')).toBeInTheDocument();
    expect(screen.getByText('0 h')).toBeInTheDocument();
  });

  it('documents en erreur : les autres indicateurs restent', async () => {
    api.mesDocuments.mockRejectedValue(new Error('500'));
    rendre();
    expect(await screen.findByText('Donnée indisponible pour le moment.')).toBeInTheDocument();
    expect(await screen.findByText('22 h / 76 h')).toBeInTheDocument();
  });

  it('séance mutualisée : comptée une fois, une seule ligne avec les deux classes', async () => {
    const paire = (id, lie, classe) => ({ ...seance('2026-11-20', '09:00', '11:00'), id, seance_liee: lie, classe_libelle: classe });
    api.monPlanning.mockResolvedValue([paire(7, 9, 'L1 MIP — 2026-2027'), paire(9, 7, 'L1 INFO — 2026-2027')]);
    rendre();
    expect(await screen.findByText('2 h')).toBeInTheDocument();
    expect(await screen.findByText('L1 MIP — 2026-2027 · L1 INFO — 2026-2027')).toBeInTheDocument();
  });

  it('avancement : un même EC dans deux classes se distingue', async () => {
    api.mesEnseignements.mockResolvedValue([
      { ...AFFECTATIONS[0], id: 1, classe: 1, classe_libelle: 'L1 MIP — 2026-2027', type_seance: 'CM' },
      { ...AFFECTATIONS[0], id: 4, classe: 2, classe_libelle: 'L1 BCG — 2026-2027', type_seance: null },
    ]);
    rendre();
    expect(await screen.findByRole('progressbar', { name: 'Avancement de ALGO1 — L1 MIP — 2026-2027 · CM' })).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: 'Avancement de ALGO1 — L1 BCG — 2026-2027' })).toBeInTheDocument();
  });

  it('lien « Tout voir » en couleur primaire (contraste AA sur carte blanche)', async () => {
    rendre();
    expect(screen.getByRole('link', { name: /Avancement/ })).toHaveClass('text-primary');
  });
});
