import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '@/api/client';
import { lireMessageConnexion } from '@/lib/messageConnexion';
import ReinitialisationPage from './ReinitialisationPage';

vi.mock('@/api/client', () => ({ default: { post: vi.fn() } }));

const MDP = 'Nouveau-UCCB-2027!';

function rendre() {
  return render(
    <MemoryRouter initialEntries={['/reinitialisation/MQ/abc-123']}>
      <Routes>
        <Route path="/reinitialisation/:uid/:jeton" element={<ReinitialisationPage />} />
        <Route path="/login" element={<p>Page de connexion</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

async function remplir(user, confirmation = MDP) {
  await user.type(screen.getByLabelText('Nouveau mot de passe'), MDP);
  await user.type(screen.getByLabelText('Confirmer le mot de passe'), confirmation);
  await user.click(screen.getByRole('button', { name: 'Enregistrer' }));
}

describe('Nouveau mot de passe', () => {
  beforeEach(() => { vi.resetAllMocks(); sessionStorage.clear(); });

  it('réinitialise puis renvoie à la connexion avec le message', async () => {
    apiClient.post.mockResolvedValue({ data: { detail: 'Mot de passe modifié. Connectez-vous.' } });
    const user = userEvent.setup();
    rendre();
    await remplir(user);
    expect(await screen.findByText('Page de connexion')).toBeInTheDocument();
    expect(apiClient.post).toHaveBeenCalledWith('/core/mot-de-passe/reinitialisation/',
      { uid: 'MQ', jeton: 'abc-123', password: MDP });
    expect(lireMessageConnexion()).toBe('Mot de passe modifié. Connectez-vous.');
  });

  it('lien invalide : message et lien vers une nouvelle demande', async () => {
    apiClient.post.mockRejectedValue({
      response: { status: 400, data: { detail: "Ce lien n'est plus valable. Faites une nouvelle demande." } } });
    const user = userEvent.setup();
    rendre();
    await remplir(user);
    expect(await screen.findByRole('alert')).toHaveTextContent("Ce lien n'est plus valable.");
    expect(screen.getByRole('link', { name: 'Faire une nouvelle demande' })).toHaveAttribute('href', '/mot-de-passe-oublie');
  });

  it('mot de passe refusé : erreur sous le champ', async () => {
    apiClient.post.mockRejectedValue({ response: { status: 400, data: { password: ['Ce mot de passe est trop court.'] } } });
    const user = userEvent.setup();
    rendre();
    await remplir(user);
    expect(await screen.findByText('Ce mot de passe est trop court.')).toBeInTheDocument();
  });

  it('confirmation différente : erreur, aucun appel', async () => {
    const user = userEvent.setup();
    rendre();
    await remplir(user, 'autre-chose-2027');
    expect(await screen.findByText('Les deux mots de passe ne correspondent pas.')).toBeInTheDocument();
    await waitFor(() => expect(apiClient.post).not.toHaveBeenCalled());
  });
});
