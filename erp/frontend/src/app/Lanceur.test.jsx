import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { lireLanceur } from '@/api/lanceur';
import useAuthStore from '@/store/authStore';
import Lanceur from './Lanceur';

vi.mock('@/api/lanceur', () => ({ lireLanceur: vi.fn() }));

const FINANCE = { module: 'finance', valeur: 26.9, unite: '%', libelle: 'des frais encaissés', detail: '24 dossiers en retard', ton: 'alerte' };
const RH = { module: 'rh', valeur: 0, unite: '', libelle: 'contrats à échéance', detail: 'Aucune vacation à confirmer', ton: 'normal' };

function connecter(modules, roles = []) {
  useAuthStore.getState().setAuth({
    accessToken: 'a', refreshToken: 'r',
    user: { id: 1, username: 'u', nom_complet: 'NGOMA Paul', modules, roles },
  });
}

const rendre = () => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <MemoryRouter>
      <Routes>
        <Route path="/" element={<Lanceur />} />
        <Route path="/moi" element={<p>Page Mon espace</p>} />
      </Routes>
    </MemoryRouter>
  </QueryClientProvider>,
);

const modulesFinanceRh = [
  { code: 'rh', libelle: 'Ressources humaines', niveaux: ['responsable'] },
  { code: 'finance', libelle: 'Finance', niveaux: ['utilisateur'] },
];

describe('Lanceur', () => {
  beforeEach(() => {
    useAuthStore.getState().clearAuth();
    lireLanceur.mockResolvedValue([FINANCE, RH]);
  });
  afterEach(() => vi.clearAllMocks());

  it('affiche une tuile par module autorisé, avec chiffre, unité et détail', async () => {
    connecter(modulesFinanceRh);
    rendre();
    const finance = screen.getByRole('link', { name: /Finance/ });
    expect(finance).toHaveAttribute('href', '/finance');
    expect(await within(finance).findByText('26,9')).toBeInTheDocument();
    expect(within(finance).getByText('%')).toBeInTheDocument();
    expect(within(finance).getByText('des frais encaissés')).toBeInTheDocument();
    expect(within(finance).getByText('24 dossiers en retard')).toBeInTheDocument();
    expect(within(screen.getByRole('link', { name: /Ressources humaines/ })).getByText('0')).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /Logistique/ })).not.toBeInTheDocument();
    expect(screen.getByText('NGOMA Paul')).toBeInTheDocument();
  });

  it('ton alerte en couleur d’avertissement', async () => {
    connecter(modulesFinanceRh);
    rendre();
    expect(await screen.findByText('26,9')).toHaveClass('text-warning');
    expect(screen.getByText('0')).not.toHaveClass('text-warning');
  });

  it('erreur du serveur : tuile sans chiffre, lien actif', async () => {
    lireLanceur.mockRejectedValue(new Error('500'));
    connecter(modulesFinanceRh);
    rendre();
    const finance = screen.getByRole('link', { name: /Finance/ });
    expect(await within(finance).findByText('—')).toBeInTheDocument();
    expect(finance).toHaveAttribute('href', '/finance');
  });

  it('valeur nulle : tuile sans chiffre', async () => {
    lireLanceur.mockResolvedValue([{ ...FINANCE, valeur: null, detail: 'Aucun frais attendu', ton: 'normal' }]);
    connecter([modulesFinanceRh[1]]);
    rendre();
    expect(await screen.findByText('Aucun frais attendu')).toBeInTheDocument();
    expect(within(screen.getByRole('link', { name: /Finance/ })).getByText('—')).toBeInTheDocument();
  });

  it('accès rapides filtrés par niveau', () => {
    connecter([{ code: 'scolarite', libelle: 'Scolarité', niveaux: ['secretariat'] }, modulesFinanceRh[1]]);
    rendre();
    const rapides = screen.getByRole('navigation', { name: 'Accès rapides' });
    expect(within(rapides).getByRole('link', { name: 'Frais étudiants' })).toHaveAttribute('href', '/finance/frais');
    expect(within(rapides).queryByRole('link', { name: 'Saisie des notes' })).not.toBeInTheDocument();
  });

  it('tuile Mon espace pour un enseignant chef de département', () => {
    connecter([{ code: 'edt', libelle: 'Emploi du temps', niveaux: ['perimetre'] }], ['enseignant', 'chef_departement']);
    rendre();
    expect(screen.getByRole('link', { name: /Mon espace/ })).toHaveAttribute('href', '/moi');
    expect(screen.getByRole('link', { name: /Emploi du temps/ })).toHaveAttribute('href', '/edt');
  });

  it('plus de bandeau ni de descriptions', () => {
    connecter(modulesFinanceRh);
    rendre();
    expect(screen.queryByText(/Frais de scolarité, paie et journal/)).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /Bonjour|Bonsoir/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/Choisissez un module/)).not.toBeInTheDocument();
  });

  it('affiche un état vide sans module', () => {
    connecter([]);
    rendre();
    expect(screen.getByText(/Aucun module ne vous est attribué/)).toBeInTheDocument();
  });

  it('redirige vers /moi un étudiant sans module', () => {
    connecter([], ['etudiant']);
    rendre();
    expect(screen.getByText('Page Mon espace')).toBeInTheDocument();
  });
});
