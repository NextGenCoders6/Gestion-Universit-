// Mot de passe oublié : l'utilisateur reçoit par e-mail un lien pour en choisir un nouveau.
// La réponse est la même qu'un compte corresponde ou non à la saisie.
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import apiClient from '@/api/client';
import { erreursServeur } from '@/lib/erreurs';
import { Alerte, BoutonEnvoi, CadrePublic, LienRetour, Ligne } from './Formulaire';
import { REQUIS } from './regles';

export default function MotDePasseOubliePage() {
  const [envoye, setEnvoye] = useState(null);
  const [erreur, setErreur] = useState(null);
  const [envoi, setEnvoi] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm({ defaultValues: { identifiant: '' } });

  const demander = async ({ identifiant }) => {
    setEnvoi(true);
    setErreur(null);
    try {
      const { data } = await apiClient.post('/core/mot-de-passe/oubli/', { identifiant: identifiant.trim() });
      setEnvoye(data.detail);
    } catch (e) {
      setErreur(erreursServeur(e).global);
    } finally {
      setEnvoi(false);
    }
  };

  return (
    <CadrePublic titre="Mot de passe oublié"
      sousTitre="Saisissez votre identifiant ou votre adresse e-mail : vous recevrez un lien pour choisir un nouveau mot de passe.">
      {envoye ? (
        <div className="space-y-4">
          <p role="status" className="rounded-lg border border-uccb-green/20 bg-uccb-green/10 p-3 text-sm font-medium text-uccb-ink">
            {envoye}
          </p>
          <LienRetour />
        </div>
      ) : (
        <form className="space-y-4" noValidate onSubmit={handleSubmit(demander)}>
          <Ligne id="identifiant" label="Identifiant ou e-mail" autoComplete="username"
            erreur={errors.identifiant?.message} {...register('identifiant', REQUIS)} />
          {erreur && <Alerte>{erreur}</Alerte>}
          <BoutonEnvoi envoi={envoi}>Envoyer le lien</BoutonEnvoi>
          <LienRetour />
        </form>
      )}
    </CadrePublic>
  );
}
