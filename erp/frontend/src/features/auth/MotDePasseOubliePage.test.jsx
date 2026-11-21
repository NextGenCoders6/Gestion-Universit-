import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '@/api/client';
import LoginPage from './LoginPage';
import MotDePasseOubliePage from './MotDePasseOubliePage';

vi.mock('@/api/client', () => ({ default: { post: vi.fn() } }));

const NEUTRE = "Si un compte correspond, un e-mail contenant un lien vient d'être envoyé.";

describe('Mot de passe oublié', () => {
  beforeEach(() => vi.resetAllMocks());

  it('envoie l’identifiant et affiche le message neutre', async () => {
    apiClient.post.mockResolvedValue({ data: { detail: NEUTRE } });
    const user = userEvent.setup();
    render(<MemoryRouter><MotDePasseOubliePage /></MemoryRouter>);
    await user.type(screen.getByLabelText('Identifiant ou e-mail'), 'divine');
    await user.click(screen.getByRole('button', { name: 'Envoyer le lien' }));
    expect(await screen.findByText(NEUTRE)).toBeInTheDocument();
    expect(apiClient.post).toHaveBeenCalledWith('/core/mot-de-passe/oubli/', { identifiant: 'divine' });
    expect(screen.queryByLabelText('Identifiant ou e-mail')).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Retour à la connexion' })).toHaveAttribute('href', '/login');
  });

  it('champ vide : erreur, aucun appel', async () => {
    const user = userEvent.setup();
    render(<MemoryRouter><MotDePasseOubliePage /></MemoryRouter>);
    await user.click(screen.getByRole('button', { name: 'Envoyer le lien' }));
    expect(await screen.findByText('Ce champ est obligatoire.')).toBeInTheDocument();
    expect(apiClient.post).not.toHaveBeenCalled();
  });

  it('la page de connexion mène à la demande', () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter><LoginPage /></MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByRole('link', { name: 'Mot de passe oublié ?' })).toHaveAttribute('href', '/mot-de-passe-oublie');
    expect(screen.queryByText(/Contactez l’administration/)).not.toBeInTheDocument();
  });
});
