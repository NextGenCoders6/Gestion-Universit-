// Nouveau mot de passe, depuis le lien reçu par e-mail (/reinitialisation/:uid/:jeton).
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate, useParams } from 'react-router-dom';
import apiClient from '@/api/client';
import { erreursServeur } from '@/lib/erreurs';
import { noterMessageConnexion } from '@/lib/messageConnexion';
import { Alerte, BoutonEnvoi, CadrePublic, LienRetour, Ligne } from './Formulaire';
import { AIDE_MOT_DE_PASSE, REQUIS, confirmationIdentique } from './regles';

export default function ReinitialisationPage() {
  const { uid, jeton } = useParams();
  const navigate = useNavigate();
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const [envoi, setEnvoi] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm({ defaultValues: { password: '', confirmation: '' } });

  const enregistrer = async ({ password }) => {
    setEnvoi(true);
    setErreurs({ champs: {}, global: null });
    try {
      const { data } = await apiClient.post('/core/mot-de-passe/reinitialisation/', { uid, jeton, password });
      noterMessageConnexion(data.detail);
      navigate('/login', { replace: true });
    } catch (e) {
      setErreurs(erreursServeur(e, ['password']));
    } finally {
      setEnvoi(false);
    }
  };
  const erreur = (n) => erreurs.champs[n] ?? errors[n]?.message;

  return (
    <CadrePublic titre="Nouveau mot de passe" sousTitre="Choisissez le mot de passe de votre compte.">
      <form className="space-y-4" noValidate onSubmit={handleSubmit(enregistrer)}>
        <Ligne id="password" label="Nouveau mot de passe" type="password" autoComplete="new-password"
          erreur={erreur('password')} aide={AIDE_MOT_DE_PASSE} {...register('password', REQUIS)} />
        <Ligne id="confirmation" label="Confirmer le mot de passe" type="password" autoComplete="new-password"
          erreur={erreur('confirmation')} {...register('confirmation', { ...REQUIS, validate: confirmationIdentique })} />
        {erreurs.global && (
          <Alerte>
            {erreurs.global}
            <LienRetour to="/mot-de-passe-oublie">Faire une nouvelle demande</LienRetour>
          </Alerte>
        )}
        <BoutonEnvoi envoi={envoi}>Enregistrer</BoutonEnvoi>
        <LienRetour />
      </form>
    </CadrePublic>
  );
}
