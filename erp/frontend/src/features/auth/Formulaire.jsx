// Éléments communs des pages publiques du compte (activation, mot de passe oublié,
// nouveau mot de passe) : même charte que la page de connexion.
import { forwardRef } from 'react';
import { Link } from 'react-router-dom';
import { Loader2 } from '@/components/ui/icons';
import logoUccb from '@/assets/login/logo-uccb.svg';

const CHAMP = 'w-full h-[46px] box-border rounded-lg border border-[#BDB8AE] px-3.5 text-[16px] text-uccb-ink bg-white '
  + 'outline-none focus:border-2 focus:border-uccb-green focus:ring-4 focus:ring-uccb-green/20 transition';

// forwardRef : react-hook-form a besoin de la ref de l'input pour lire sa valeur.
export const Ligne = forwardRef(function Ligne({ id, label, type = 'text', erreur, aide, ...props }, ref) {
  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-sm font-semibold text-uccb-ink">{label}</label>
      <input id={id} ref={ref} type={type} className={CHAMP} aria-invalid={erreur ? 'true' : undefined} {...props} />
      {aide && !erreur && <p className="mt-1 text-xs text-[#4A4741]">{aide}</p>}
      {erreur && <p className="mt-1 text-xs font-medium text-uccb-red">{erreur}</p>}
    </div>
  );
});

export function CadrePublic({ titre, sousTitre, children }) {
  return (
    <main className="flex min-h-screen items-center justify-center bg-[#F6F4EF] px-4 py-10">
      <div className="w-full max-w-[460px] rounded-2xl border border-[#E4DFD5] bg-white p-7 shadow-sm">
        <div className="mb-6 flex items-center gap-3">
          <img src={logoUccb} alt="" className="size-12" />
          <div>
            <h1 className="text-xl font-bold text-uccb-ink">{titre}</h1>
            <p className="text-sm text-[#4A4741]">{sousTitre}</p>
          </div>
        </div>
        {children}
      </div>
    </main>
  );
}

export function Alerte({ children }) {
  return (
    <div role="alert" className="rounded-lg border border-uccb-red/20 bg-uccb-red/10 p-3 text-sm font-medium text-uccb-red">
      {children}
    </div>
  );
}

export function BoutonEnvoi({ envoi, children }) {
  return (
    <button type="submit" disabled={envoi}
      className="flex h-[48px] w-full items-center justify-center gap-2 rounded-lg bg-uccb-green font-bold text-white transition hover:brightness-95 disabled:opacity-60">
      {envoi && <Loader2 className="size-4 animate-spin" />} {children}
    </button>
  );
}

export function LienRetour({ to = '/login', children = 'Retour à la connexion' }) {
  return (
    <p className="text-center text-sm">
      <Link to={to} className="font-semibold text-uccb-green underline underline-offset-4">{children}</Link>
    </p>
  );
}
