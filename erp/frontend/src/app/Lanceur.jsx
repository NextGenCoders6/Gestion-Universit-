import { Link } from 'react-router-dom';
import { ArrowRightCircle, Inbox, UserCircle } from '@/components/ui/icons';
import logoUccb from '@/assets/login/logo-uccb.svg';
import useAuthStore, { aRole } from '@/store/authStore';
import MenuUtilisateur from './MenuUtilisateur';
import { COULEUR_MON_ESPACE, modulesVisibles, styleModule } from './modules';

function Tuile({ to, libelle, description, icone: Icone, couleur }) {
  return (
    <Link
      to={to}
      style={styleModule({ couleur })}
      className="carte-interactive group relative flex flex-col gap-4 overflow-hidden p-6 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span aria-hidden className="absolute inset-x-0 top-0 h-1 bg-module" />
      <span aria-hidden className="pointer-events-none absolute -right-10 -top-10 size-32 rounded-full bg-module/[0.07] transition-transform duration-300 group-hover:scale-125" />
      <span className="relative flex size-12 items-center justify-center rounded-xl bg-module/10 text-module ring-1 ring-module/20">
        <Icone className="size-6" />
      </span>
      <span className="relative">
        <span className="block text-base font-semibold tracking-tight text-foreground">{libelle}</span>
        {description && <span className="mt-1 block text-sm leading-relaxed text-muted-foreground">{description}</span>}
      </span>
      <span className="relative mt-auto flex items-center gap-1 text-sm font-medium text-module opacity-0 transition-opacity group-hover:opacity-100">
        Ouvrir <ArrowRightCircle className="size-4" />
      </span>
    </Link>
  );
}

function dateDuJour() {
  const texte = new Intl.DateTimeFormat('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(new Date());
  return texte.charAt(0).toUpperCase() + texte.slice(1);
}

function salutation() {
  const h = new Date().getHours();
  return h < 18 ? 'Bonjour' : 'Bonsoir';
}

/** Accueil après connexion : une tuile par module autorisé, comme le lanceur d'Odoo. */
export default function Lanceur() {
  const user = useAuthStore((state) => state.user);
  const espacePersonnel = useAuthStore((state) => aRole(state, 'etudiant') || aRole(state, 'enseignant'));
  const modules = modulesVisibles(user);
  const vide = modules.length === 0 && !espacePersonnel;

  return (
    <div className="min-h-dvh bg-canvas">
      <header className="sticky top-0 z-40 flex h-16 items-center justify-between border-b border-white/10 bg-sidebar px-4 text-sidebar-foreground md:px-8">
        <div className="flex items-center gap-3">
          <span className="flex size-9 items-center justify-center rounded-lg bg-white p-1 shadow-sm">
            <img src={logoUccb} alt="" className="size-full" />
          </span>
          <div className="leading-tight">
            <h1 className="text-[15px] font-bold tracking-tight">UCCB</h1>
            <p className="text-[11px] text-sidebar-muted">Système de gestion de l’université</p>
          </div>
        </div>
        <div className="rounded-lg bg-white text-foreground"><MenuUtilisateur /></div>
      </header>

      <section className="relative overflow-hidden bg-sidebar text-sidebar-foreground">
        <div aria-hidden className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,hsl(var(--primary)/0.55),transparent_60%)]" />
        <div aria-hidden className="absolute -bottom-24 -left-16 size-72 rounded-full bg-white/[0.04]" />
        <div className="relative mx-auto max-w-6xl px-4 pb-24 pt-10 md:px-8">
          <p className="text-sm font-medium text-sidebar-muted">{dateDuJour()}</p>
          <h2 className="mt-2 text-3xl font-semibold tracking-tight md:text-4xl">
            {`${salutation()}, ${user?.nom_complet ?? ''}`}
          </h2>
          <p className="mt-2 max-w-xl text-sidebar-muted">Choisissez un module pour commencer. Vous ne voyez que ceux qui vous sont attribués.</p>
        </div>
      </section>

      <main className="relative mx-auto -mt-14 max-w-6xl px-4 pb-12 md:px-8">
        <h2 className="mb-4 text-xs font-semibold uppercase tracking-[0.14em] text-white/80">Vos modules</h2>
        {vide ? (
          <div className="carte flex flex-col items-center gap-3 py-16 text-center">
            <Inbox className="size-10 text-muted-foreground" />
            <p className="max-w-sm text-sm text-muted-foreground">
              Aucun module ne vous est attribué. Contactez l’administrateur.
            </p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {espacePersonnel && (
                <Tuile to="/moi" libelle="Mon espace" description="Votre planning, vos notes et vos documents."
                  icone={UserCircle} couleur={COULEUR_MON_ESPACE} />
              )}
              {modules.map((m) => (
                <Tuile key={m.code} to={m.chemin} libelle={m.libelle} description={m.description} icone={m.icone} couleur={m.couleur} />
              ))}
            </div>
          </>
        )}
      </main>
    </div>
  );
}
