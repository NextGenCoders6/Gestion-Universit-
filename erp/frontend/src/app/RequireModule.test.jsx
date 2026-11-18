import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Link, MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import useAuthStore from '@/store/authStore';
import RequireAuth from './RequireAuth';
import RequireModule from './RequireModule';
import { fetchMoi } from '@/api/auth';

vi.mock('@/api/auth', () => ({ fetchMoi: vi.fn(() => new Promise(() => {})) }));

function connecter(modules) {
  useAuthStore.getState().setAuth({
    accessToken: 'a', refreshToken: 'r', user: { id: 1, username: 'u', nom_complet: 'U', modules, roles: [] },
  });
}

function Login() {
  const location = useLocation();
  return <p>Connexion — retour vers {location.state?.from?.pathname}</p>;
}

function arbre(chemin) {
  return render(
    <MemoryRouter initialEntries={[chemin]}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<RequireAuth />}>
          <Route path="/parametres" element={<RequireModule module="parametres"><p>Écran Paramètres</p></RequireModule>} />
          <Route path="/rh" element={<RequireModule module="rh" niveau="responsable"><p>Écran RH</p></RequireModule>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe('gardes de route', () => {
  beforeEach(() => useAuthStore.getState().clearAuth());

  it('RequireAuth redirige vers /login en gardant la page demandée', () => {
    arbre('/rh');
    expect(screen.getByText('Connexion — retour vers /rh')).toBeInTheDocument();
  });

  it('RequireModule sans droit affiche 403 sans changer de page', () => {
    connecter([{ code: 'rh', niveaux: ['responsable'] }]);
    arbre('/parametres');
    expect(screen.getByText(/Accès non autorisé/)).toBeInTheDocument();
    expect(screen.queryByText('Écran Paramètres')).not.toBeInTheDocument();
  });

  it('RequireModule vérifie le niveau', () => {
    connecter([{ code: 'rh', niveaux: ['utilisateur'] }]);
    arbre('/rh');
    expect(screen.getByText(/Accès non autorisé/)).toBeInTheDocument();
  });

  it('RequireModule avec droit affiche l’écran', () => {
    connecter([{ code: 'parametres', niveaux: ['responsable'] }]);
    arbre('/parametres');
    expect(screen.getByText('Écran Paramètres')).toBeInTheDocument();
  });

  it('RequireAuth relit le profil à chaque changement de page', async () => {
    fetchMoi.mockClear();
    connecter([{ code: 'parametres', niveaux: ['responsable'] }]);
    render(
      <MemoryRouter initialEntries={['/a']}>
        <Routes>
          <Route element={<RequireAuth />}>
            <Route path="/a" element={<Link to="/b">aller</Link>} />
            <Route path="/b" element={<p>page b</p>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );
    expect(fetchMoi).toHaveBeenCalledTimes(1);
    await userEvent.setup().click(screen.getByText('aller'));
    expect(await screen.findByText('page b')).toBeInTheDocument();
    expect(fetchMoi).toHaveBeenCalledTimes(2);
  });
});
