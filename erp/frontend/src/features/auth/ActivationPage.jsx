// Première connexion d'un étudiant : il active son compte avec les informations
// enregistrées par le secrétariat, puis choisit son mot de passe.
import { forwardRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { Link, useNavigate } from 'react-router-dom';
import { Loader2 } from '@/components/ui/icons';
import apiClient from '@/api/client';
import { erreursServeur } from '@/lib/erreurs';
import { noterMessageConnexion } from '@/lib/messageConnexion';
import logoUccb from '@/assets/login/logo-uccb.svg';

const CHAMP = 'w-full h-[46px] box-border rounded-lg border border-[#BDB8AE] px-3.5 text-[16px] text-uccb-ink bg-white '
  + 'outline-none focus:border-2 focus:border-uccb-green focus:ring-4 focus:ring-uccb-green/20 transition';

// forwardRef : react-hook-form a besoin de la ref de l'input pour lire sa valeur.
const Ligne = forwardRef(function Ligne({ id, label, type = 'text', erreur, aide, ...props }, ref) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-uccb-ink">{label}</label>
      <input id={id} ref={ref} type={type} className={CHAMP} aria-invalid={erreur ? 'true' : undefined} {...props} />
      {aide && !erreur && <p className="mt-1 text-xs text-[#4A4741]">{aide}</p>}
      {erreur && <p className="mt-1 text-xs font-medium text-uccb-red">{erreur}</p>}
    </div>
  );
});

export default function ActivationPage() {
  const navigate = useNavigate();
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const [envoi, setEnvoi] = useState(false);
  const { register, handleSubmit, formState: { errors } } = useForm({
    defaultValues: { matricule: '', email: '', date_naissance: '', password: '', confirmation: '' },
  });
  const requis = { required: 'Ce champ est obligatoire.' };

  const activer = async ({ matricule, email, date_naissance, password }) => {
    setEnvoi(true);
    setErreurs({ champs: {}, global: null });
    try {
      const { data } = await apiClient.post('/scolarite/activation/', { matricule: matricule.trim(), email, date_naissance, password });
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
    <main className="flex min-h-screen items-center justify-center bg-[#F6F4EF] px-4 py-10">
      <div className="w-full max-w-[460px] rounded-2xl border border-[#E4DFD5] bg-white p-7 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <img src={logoUccb} alt="" className="size-12" />
          <div>
            <h1 className="text-xl font-bold text-uccb-ink">Activer mon compte étudiant</h1>
            <p className="text-sm text-[#4A4741]">Saisissez les informations données au secrétariat lors de votre inscription.</p>
          </div>
        </div>
        <form className="space-y-4" noValidate onSubmit={handleSubmit(activer)}>
          <Ligne id="matricule" label="Matricule" autoComplete="username" erreur={erreur('matricule')} {...register('matricule', requis)} />
          <Ligne id="email" label="E-mail" type="email" autoComplete="email" erreur={erreur('email')} {...register('email', requis)} />
          <Ligne id="date_naissance" label="Date de naissance" type="date" erreur={erreur('date_naissance')}
            {...register('date_naissance', requis)} />
          <Ligne id="password" label="Mot de passe" type="password" autoComplete="new-password" erreur={erreur('password')}
            aide="Au moins 8 caractères, pas uniquement des chiffres." {...register('password', requis)} />
          <Ligne id="confirmation" label="Confirmer le mot de passe" type="password" autoComplete="new-password"
            erreur={erreur('confirmation')} {...register('confirmation', {
              ...requis, validate: (v, tout) => v === tout.password || 'Les deux mots de passe ne correspondent pas.' })} />
          {erreurs.global && (
            <div role="alert" className="rounded-lg border border-uccb-red/20 bg-uccb-red/10 p-3 text-sm font-medium text-uccb-red">
              {erreurs.global}
            </div>
          )}
          <button type="submit" disabled={envoi}
            className="flex h-[48px] w-full items-center justify-center gap-2 rounded-lg bg-uccb-green font-bold text-white transition hover:brightness-95 disabled:opacity-60">
            {envoi && <Loader2 className="size-4 animate-spin" />} Activer mon compte
          </button>
          <p className="text-center text-sm"><Link to="/login" className="font-semibold text-uccb-green underline underline-offset-4">Retour à la connexion</Link></p>
        </form>
      </div>
    </main>
  );
}
