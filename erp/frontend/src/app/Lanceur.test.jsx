import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import useAuthStore from '@/store/authStore';
import Lanceur from './Lanceur';

function connecter(modules, roles = []) {
  useAuthStore.getState().setAuth({
    accessToken: 'a', refreshToken: 'r',
    user: { id: 1, username: 'u', nom_complet: 'NGOMA Paul', modules, roles },
  });
}

const rendre = () => render(
  <MemoryRouter>
    <Routes>
      <Route path="/" element={<Lanceur />} />
      <Route path="/moi" element={<p>Page Mon espace</p>} />
    </Routes>
  </MemoryRouter>,
);

describe('Lanceur', () => {
  beforeEach(() => useAuthStore.getState().clearAuth());

  it('affiche seulement les modules autorisés', () => {
    connecter([{ code: 'rh', libelle: 'Ressources humaines', niveaux: ['responsable'] }]);
    rendre();
    expect(screen.getByRole('link', { name: /Ressources humaines/ })).toHaveAttribute('href', '/rh');
    expect(screen.queryByRole('link', { name: /Finance/ })).not.toBeInTheDocument();
    expect(screen.getByText('NGOMA Paul')).toBeInTheDocument();
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

  it('redirige vers /moi un enseignant sans module', () => {
    connecter([], ['enseignant']);
    rendre();
    expect(screen.getByText('Page Mon espace')).toBeInTheDocument();
  });

  it('garde le lanceur pour un enseignant avec un module', () => {
    connecter([{ code: 'edt', libelle: 'Emploi du temps', niveaux: ['utilisateur'] }], ['enseignant', 'chef_departement']);
    rendre();
    expect(screen.getByRole('link', { name: /Emploi du temps/ })).toHaveAttribute('href', '/edt');
    expect(screen.getByRole('link', { name: /Mon espace/ })).toHaveAttribute('href', '/moi');
    expect(screen.queryByText('Page Mon espace')).not.toBeInTheDocument();
  });
});
