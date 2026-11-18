import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it } from 'vitest';
import useAuthStore from '@/store/authStore';
import Lanceur from './Lanceur';

function connecter(modules, roles = []) {
  useAuthStore.getState().setAuth({
    accessToken: 'a', refreshToken: 'r',
    user: { id: 1, username: 'u', nom_complet: 'NGOMA Paul', modules, roles },
  });
}

const rendre = () => render(<MemoryRouter><Lanceur /></MemoryRouter>);

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

  it('ajoute « Mon espace » pour un enseignant', () => {
    connecter([], ['enseignant']);
    rendre();
    expect(screen.getByRole('link', { name: /Mon espace/ })).toHaveAttribute('href', '/moi');
    expect(screen.queryByText(/Aucun module ne vous est attribué/)).not.toBeInTheDocument();
  });
});
