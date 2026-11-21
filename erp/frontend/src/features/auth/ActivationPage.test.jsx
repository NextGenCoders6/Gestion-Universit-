import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import apiClient from '@/api/client';
import { lireMessageConnexion } from '@/lib/messageConnexion';
import ActivationPage from './ActivationPage';

vi.mock('@/api/client', () => ({ default: { post: vi.fn() } }));

function rendre() {
  return render(
    <MemoryRouter initialEntries={['/activation']}>
      <Routes>
        <Route path="/activation" element={<ActivationPage />} />
        <Route path="/login" element={<p>Page de connexion</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

async function remplir(user, { confirmation = 'Etudiant-UCCB-2026!' } = {}) {
  await user.type(screen.getByLabelText('Matricule'), 'UCCB26MOUDI00001');
  await user.type(screen.getByLabelText('E-mail'), 'divine@example.org');
  await user.type(screen.getByLabelText('Date de naissance'), '2006-03-14');
  await user.type(screen.getByLabelText('Mot de passe'), 'Etudiant-UCCB-2026!');
  await user.type(screen.getByLabelText('Confirmer le mot de passe'), confirmation);
  await user.click(screen.getByRole('button', { name: 'Activer mon compte' }));
}

describe('Activation du compte', () => {
  beforeEach(() => { vi.resetAllMocks(); sessionStorage.clear(); });

  it('succès : retour à la connexion avec un message', async () => {
    apiClient.post.mockResolvedValue({ data: { detail: 'Compte activé. Connectez-vous avec votre matricule.', username: 'UCCB26MOUDI00001' } });
    const user = userEvent.setup();
    rendre();
    await remplir(user);
    expect(await screen.findByText('Page de connexion')).toBeInTheDocument();
    expect(apiClient.post).toHaveBeenCalledWith('/core/activation/', {
      matricule: 'UCCB26MOUDI00001', email: 'divine@example.org', date_naissance: '2006-03-14', password: 'Etudiant-UCCB-2026!' });
    expect(lireMessageConnexion()).toMatch(/Compte activé/);
  });

  it('échec : message du serveur', async () => {
    apiClient.post.mockRejectedValue({ response: { status: 400, data: { detail: 'Informations incorrectes ou compte déjà activé.' } } });
    const user = userEvent.setup();
    rendre();
    await remplir(user);
    expect(await screen.findByRole('alert')).toHaveTextContent('Informations incorrectes ou compte déjà activé.');
  });

  it('les deux mots de passe doivent être identiques', async () => {
    const user = userEvent.setup();
    rendre();
    await remplir(user, { confirmation: 'autre-chose-2026' });
    expect(await screen.findByText('Les deux mots de passe ne correspondent pas.')).toBeInTheDocument();
    await waitFor(() => expect(apiClient.post).not.toHaveBeenCalled());
  });
});
