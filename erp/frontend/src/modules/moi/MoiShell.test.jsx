import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuthStore from '@/store/authStore';
import { routesMoi } from './routes';

vi.mock('./api', () => ({
  monPlanning: vi.fn(() => Promise.resolve([])),
  mesEnseignements: vi.fn(() => Promise.resolve([])),
  mesDocuments: vi.fn(() => Promise.resolve([])),
  mesNotes: vi.fn(() => Promise.resolve({ matricule: 'M', inscriptions: [] })),
  monPlanningEtudiant: vi.fn(() => Promise.resolve([])),
  mesEnseignants: vi.fn(() => Promise.resolve([])),
  mesFrais: vi.fn(() => Promise.resolve([])),
}));
vi.mock('@/modules/edt/components/PlanningGrid', () => ({ default: () => <div>grille</div> }));

function connecter(roles, modules = []) {
  useAuthStore.getState().setAuth({
    accessToken: 'a', refreshToken: 'r', user: { id: 1, username: 'u', nom_complet: 'U', roles, modules },
  });
}

function rendre(chemin = '/moi') {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[chemin]}>
        <Routes><Route path="/moi/*" element={routesMoi()} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Mon espace', () => {
  beforeEach(() => useAuthStore.getState().clearAuth());

  it('un enseignant voit planning, enseignements et documents', async () => {
    connecter(['enseignant']);
    rendre('/moi/planning');
    expect(await screen.findByText('grille')).toBeInTheDocument();
    for (const nom of ['Mon planning', 'Mes enseignements', 'Mes documents']) {
      expect(screen.getAllByRole('link', { name: nom }).length).toBeGreaterThan(0);
    }
  });

  it('un étudiant voit ses notes, son planning et ses enseignants', async () => {
    connecter(['etudiant']);
    rendre('/moi/notes');
    expect((await screen.findAllByRole('heading', { name: 'Mes notes' })).length).toBeGreaterThan(0);
    for (const nom of ['Mes notes', 'Mon planning', 'Mes enseignants', 'Mes frais']) {
      expect(screen.getAllByRole('link', { name: nom }).length).toBeGreaterThan(0);
    }
    expect(screen.queryByRole('link', { name: 'Mes documents' })).not.toBeInTheDocument();
  });

  it('sans rôle : message d’attente', async () => {
    connecter([]);
    rendre('/moi');
    expect(await screen.findByText(/Aucun espace personnel/)).toBeInTheDocument();
  });

  it('masque « Tous les modules » sans autre module', async () => {
    connecter(['etudiant']);
    rendre('/moi/notes');
    expect((await screen.findAllByRole('heading', { name: 'Mes notes' })).length).toBeGreaterThan(0);
    expect(screen.queryByRole('link', { name: 'Retour aux modules' })).not.toBeInTheDocument();
  });

  it('montre « Tous les modules » avec un module', async () => {
    connecter(['enseignant'], [{ code: 'edt', libelle: 'Emploi du temps', niveaux: ['utilisateur'] }]);
    rendre('/moi/planning');
    expect(await screen.findByText('grille')).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Retour aux modules' }).length).toBeGreaterThan(0);
  });

  it('ouvre l’accueil par défaut pour un étudiant', async () => {
    connecter(['etudiant']);
    rendre('/moi');
    expect(await screen.findByRole('heading', { name: /^(Bonjour|Bonsoir), U$/ })).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: 'Accueil' }).length).toBeGreaterThan(0);
    expect(screen.getByText('Moyenne du dernier semestre')).toBeInTheDocument();
  });

  it('ouvre l’accueil par défaut pour un enseignant', async () => {
    connecter(['enseignant']);
    rendre('/moi');
    expect(await screen.findByRole('heading', { name: /^(Bonjour|Bonsoir), U$/ })).toBeInTheDocument();
    expect(screen.getByText('Documents déposés')).toBeInTheDocument();
  });
});
