import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import useAuthStore from '@/store/authStore';
import * as api from '../api';
import AccueilEtudiant from './AccueilEtudiant';

vi.mock('../api', () => ({
  mesNotes: vi.fn(), monPlanningEtudiant: vi.fn(), mesEnseignants: vi.fn(), mesFrais: vi.fn(),
}));

const NOTES = { matricule: 'M', inscriptions: [{ resultats_masques: false, semestres: [
  { semestre: 'S1', deliberee: true, resultat: { moyenne: 6.98, decision: 'AJOURNÉ' } },
  { semestre: 'S2', deliberee: false, resultat: null }] }] };
const seance = (jour, debut, fin) => ({
  id: `${jour}${debut}`, ec_code: 'ALGO1', ec_libelle: 'Algorithmique 1', enseignant_nom: 'MBEMBA Christelle',
  creneau_effectif: { jour, debut, fin },
});
const FRAIS = [{ id: 1, inscription_statut: 'active', reste: 1200000, en_retard: false,
  prochaine_echeance: { mois: '2026-12', date_limite: '2027-01-05', montant: 150000, paye: 0 } }];
const ENSEIGNANTS = [{ id: 6, nom_complet: 'MBEMBA Christelle', grade: 'Docteur', ecs: [{ id: 1, code: 'ALGO1' }, { id: 2, code: 'ARCHI1' }] }];

function rendre() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><MemoryRouter><AccueilEtudiant /></MemoryRouter></QueryClientProvider>);
}

describe('Accueil étudiant', () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date(2026, 10, 19, 9, 30));
    useAuthStore.getState().setAuth({ accessToken: 'a', refreshToken: 'r',
      user: { id: 1, username: 'etudiant', nom_complet: 'MABIALA Grâce', roles: ['etudiant'], modules: [] } });
    api.mesNotes.mockResolvedValue(NOTES);
    api.monPlanningEtudiant.mockResolvedValue([seance('2026-11-19', '08:00', '10:00'), seance('2026-11-20', '14:00', '16:00')]);
    api.mesEnseignants.mockResolvedValue(ENSEIGNANTS);
    api.mesFrais.mockResolvedValue(FRAIS);
  });
  afterEach(() => { vi.useRealTimers(); vi.clearAllMocks(); });

  it('salue, résume notes, cours, frais et enseignants', async () => {
    rendre();
    expect(screen.getByRole('heading', { name: 'Bonjour, MABIALA Grâce' })).toBeInTheDocument();
    expect(screen.getByText('Jeudi 19 novembre 2026')).toBeInTheDocument();
    expect(await screen.findByText('6,98 /20')).toBeInTheDocument();
    expect(screen.getByText('S1 · AJOURNÉ')).toBeInTheDocument();
    expect(await screen.findByText('4 h')).toBeInTheDocument();
    // montant en grand, unité « FCFA » à part en plus petit : la valeur tient sur une ligne
    expect(await screen.findByText(/^1\s200\s000$/)).toBeInTheDocument();
    expect(screen.getByText(/^150\s000$/)).toBeInTheDocument();
    expect(screen.getAllByText('FCFA')).toHaveLength(2);
    expect(screen.getByText('avant le 05/01/2027')).toBeInTheDocument();
    expect((await screen.findAllByText('ALGO1 — Algorithmique 1')).length).toBe(2);
    expect(screen.getAllByText('MBEMBA Christelle').length).toBe(3);   // 2 cours + la carte enseignant
    expect(screen.getByText('Docteur · ALGO1, ARCHI1')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Prochains cours/ })).toHaveAttribute('href', '/moi/planning');
    expect(screen.getByRole('link', { name: /Mes enseignants/ })).toHaveAttribute('href', '/moi/enseignants');
    expect(api.monPlanningEtudiant).toHaveBeenCalledWith({ date_debut: '2026-11-16', date_fin: '2026-11-22' });
    expect(api.monPlanningEtudiant).toHaveBeenCalledWith({ date_debut: '2026-11-19', date_fin: '2026-12-03' });
  });

  it('résultats masqués : pas de moyenne, message affiché', async () => {
    api.mesNotes.mockResolvedValue({ inscriptions: [{ resultats_masques: true, message_resultats: 'Réglez vos frais.', semestres: [
      { semestre: 'S1', deliberee: true, resultat: { moyenne: 6.98, decision: 'AJOURNÉ' } }] }] });
    rendre();
    expect(await screen.findByText('Réglez vos frais.')).toBeInTheDocument();
    expect(screen.queryByText('6,98 /20')).not.toBeInTheDocument();
  });

  it('frais en erreur : les autres cartes restent', async () => {
    api.mesFrais.mockRejectedValue(new Error('500'));
    rendre();
    expect((await screen.findAllByText('Donnée indisponible pour le moment.')).length).toBeGreaterThan(0);
    expect(await screen.findByText('6,98 /20')).toBeInTheDocument();
    expect(screen.getAllByText('MBEMBA Christelle').length).toBeGreaterThan(0);
  });

  it('aucun cours à venir, aucun résultat, aucun dossier', async () => {
    api.monPlanningEtudiant.mockResolvedValue([]);
    api.mesNotes.mockResolvedValue({ inscriptions: [] });
    api.mesFrais.mockResolvedValue([]);
    rendre();
    expect(await screen.findByText('Aucun cours dans les 14 prochains jours.')).toBeInTheDocument();
    expect(await screen.findByText('Pas encore de résultat délibéré.')).toBeInTheDocument();
    expect((await screen.findAllByText('Aucun dossier de frais.')).length).toBeGreaterThan(0);
    expect(screen.getByText('0 h')).toBeInTheDocument();
  });

  it('mensualité en retard', async () => {
    api.mesFrais.mockResolvedValue([{ ...FRAIS[0], en_retard: true, montant_en_retard: 150000 }]);
    rendre();
    expect(await screen.findByText('Une mensualité en retard')).toBeInTheDocument();
  });
});
