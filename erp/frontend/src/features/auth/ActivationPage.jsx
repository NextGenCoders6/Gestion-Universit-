// Première connexion d'un étudiant ou d'un enseignant : il active son compte avec les
// informations enregistrées par le secrétariat ou les ressources humaines, puis choisit
// son mot de passe.
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import apiClient from '@/api/client';
import { erreursServeur } from '@/lib/erreurs';
import { noterMessageConnexion } from '@/lib/messageConnexion';
import { Alerte, BoutonEnvoi, CadrePublic, LienRetour, Ligne } from './Formulaire';
import { AIDE_MOT_DE_PASSE, REQUIS, confirmationIdentique } from './regles';

export default function ActivationPage() {
  const navigate = useNavigate();
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const [envoi, setEnvoi] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm({
    defaultValues: { matricule: '', email: '', date_naissance: '', password: '', confirmation: '' },
  });

  const activer = async ({ matricule, email, date_naissance, password }) => {
    setEnvoi(true);
    setErreurs({ champs: {}, global: null });
    try {
      const { data } = await apiClient.post('/core/activation/', { matricule: matricule.trim(), email, date_naissance, password });
      noterMessageConnexion(`${data.detail} Identifiant : ${data.username}`);
      navigate('/login', { replace: true });
    } catch (e) {
      setErreurs(erreursServeur(e, ['matricule', 'email', 'date_naissance', 'password']));
    } finally {
      setEnvoi(false);
    }
  };
  const erreur = (n) => erreurs.champs[n] ?? errors[n]?.message;

  return (
    <CadrePublic titre="Activer mon compte"
      sousTitre="Saisissez les informations données au secrétariat ou aux ressources humaines.">
      <form className="space-y-4" noValidate onSubmit={handleSubmit(activer)}>
        <Ligne id="matricule" label="Matricule" autoComplete="username" erreur={erreur('matricule')} {...register('matricule', REQUIS)} />
        <Ligne id="email" label="E-mail" type="email" autoComplete="email" erreur={erreur('email')} {...register('email', REQUIS)} />
        <Ligne id="date_naissance" label="Date de naissance" type="date" erreur={erreur('date_naissance')}
          {...register('date_naissance', REQUIS)} />
        <Ligne id="password" label="Mot de passe" type="password" autoComplete="new-password" erreur={erreur('password')}
          aide={AIDE_MOT_DE_PASSE} {...register('password', REQUIS)} />
        <Ligne id="confirmation" label="Confirmer le mot de passe" type="password" autoComplete="new-password"
          erreur={erreur('confirmation')} {...register('confirmation', { ...REQUIS, validate: confirmationIdentique })} />
        {erreurs.global && <Alerte>{erreurs.global}</Alerte>}
        <BoutonEnvoi envoi={envoi}>Activer mon compte</BoutonEnvoi>
        <LienRetour />
      </form>
    </CadrePublic>
  );
}
