import { Link } from 'react-router-dom';
import { Inbox, UserCircle } from '@/components/ui/icons';
import logoUccb from '@/assets/login/logo-uccb.svg';
import useAuthStore, { aRole } from '@/store/authStore';
import MenuUtilisateur from './MenuUtilisateur';
import { modulesVisibles } from './modules';

function Tuile({ to, libelle, description, icone: Icone }) {
  return (
    <Link
      to={to}
      className="group flex flex-col gap-3 rounded-xl border border-border bg-card p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className="flex size-12 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icone className="size-7" />
      </span>
      <span className="text-base font-semibold text-foreground group-hover:text-primary">{libelle}</span>
      {description && <span className="text-sm text-muted-foreground">{description}</span>}
    </Link>
  );
}

/** Accueil après connexion : une tuile par module autorisé, comme le lanceur d'Odoo. */
export default function Lanceur() {
  const user = useAuthStore((state) => state.user);
  const espacePersonnel = useAuthStore((state) => aRole(state, 'etudiant') || aRole(state, 'enseignant'));
  const modules = modulesVisibles(user);
  const vide = modules.length === 0 && !espacePersonnel;

  return (
    <div className="min-h-dvh bg-muted/40">
      <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border bg-background px-4 md:px-6">
        <div className="flex items-center gap-3">
          <img src={logoUccb} alt="" className="size-9" />
          <div>
            <h1 className="text-base font-bold tracking-tight text-foreground">UCCB</h1>
            <p className="text-[11px] text-muted-foreground">Système de gestion de l’université</p>
          </div>
        </div>
        <MenuUtilisateur />
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 md:px-6">
        <h2 className="mb-6 text-xl font-semibold tracking-tight text-foreground">Vos modules</h2>
        {vide ? (
          <div className="flex flex-col items-center gap-3 rounded-xl border border-dashed border-border bg-background py-16 text-center">
            <Inbox className="size-10 text-muted-foreground" />
            <p className="max-w-sm text-sm text-muted-foreground">
              Aucun module ne vous est attribué. Contactez l’administrateur.
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {espacePersonnel && (
              <Tuile
                to="/moi"
                libelle="Mon espace"
                description="Votre planning, vos notes et vos documents."
                icone={UserCircle}
              />
            )}
            {modules.map((m) => (
              <Tuile key={m.code} to={m.chemin} libelle={m.libelle} description={m.description} icone={m.icone} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
