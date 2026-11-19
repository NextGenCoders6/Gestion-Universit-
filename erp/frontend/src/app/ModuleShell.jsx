/**
 * Layout d'un module : barre latérale vert profond propre au module, barre supérieure
 * translucide avec fil d'Ariane, zone de contenu sur la toile, toasts et confirmations.
 * La couleur du module (modules.js → couleur) est posée dans --module : tuiles, accents.
 */
import { useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { ConfirmDialogHost } from '@/components/shared/ConfirmDialog';
import { ChevronRight, LayoutGrid, LogOut, Menu } from '@/components/ui/icons';
import logoUccb from '@/assets/login/logo-uccb.svg';
import { logout } from '@/api/auth';
import useAuthStore, { niveauxModule } from '@/store/authStore';
import { cn } from '@/lib/utils';
import MenuUtilisateur from './MenuUtilisateur';
import { menuVisible, styleModule } from './modules';

function ModuleSidebar({ module, onNavigate }) {
  const niveaux = useAuthStore((state) => niveauxModule(state, module.code));
  const items = menuVisible(module, niveaux);
  const IconeModule = module.icone;

  return (
    <aside className="relative flex h-full w-[264px] select-none flex-col overflow-hidden bg-sidebar text-sidebar-foreground">
      {/* Halo discret aux couleurs du module, en haut de la barre. */}
      <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 h-48 bg-gradient-to-b from-module/25 to-transparent" />

      <div className="relative flex h-16 items-center gap-3 px-5">
        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-white p-1 shadow-sm">
          <img src={logoUccb} alt="" className="size-full" />
        </span>
        <div className="min-w-0 leading-tight">
          <p className="text-[15px] font-bold tracking-tight">UCCB</p>
          <p className="truncate text-[11px] text-sidebar-muted">Université Catholique du Congo-Brazzaville</p>
        </div>
      </div>

      <div className="relative mx-4 mb-2 flex items-center gap-3 rounded-xl bg-white/[0.06] p-3 ring-1 ring-white/10">
        {IconeModule && (
          <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-module text-white shadow-md shadow-black/20">
            <IconeModule className="size-5" />
          </span>
        )}
        <div className="min-w-0">
          <p className="text-[11px] font-medium uppercase tracking-wider text-sidebar-muted">Module</p>
          <p className="truncate text-sm font-semibold">{module.libelle}</p>
        </div>
      </div>

      <nav className="relative flex-1 space-y-0.5 overflow-y-auto px-3 py-3">
        {items.map((item) => {
          const Icone = item.icone;
          return (
            <NavLink
              key={item.chemin}
              to={`${module.chemin}/${item.chemin}`}
              onClick={onNavigate}
              className={({ isActive }) => cn(
                'group relative flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors duration-150',
                isActive
                  ? 'bg-white/[0.12] text-white before:absolute before:inset-y-2 before:left-0 before:w-1 before:rounded-r-full before:bg-module'
                  : 'text-sidebar-muted hover:bg-white/[0.06] hover:text-white',
              )}
            >
              {Icone && <Icone className="h-[18px] w-[18px] shrink-0 opacity-90" />}
              <span className="truncate">{item.libelle}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="relative space-y-1 border-t border-white/10 p-3">
        <Link
          to="/"
          onClick={onNavigate}
          aria-label="Retour aux modules"
          className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-sidebar-muted transition-colors hover:bg-white/[0.06] hover:text-white"
        >
          <LayoutGrid className="h-[18px] w-[18px] shrink-0" />
          <span>Tous les modules</span>
        </Link>
        <button
          type="button"
          onClick={() => logout()}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm font-medium text-sidebar-muted transition-colors duration-150 hover:bg-red-500/15 hover:text-red-200"
        >
          <LogOut className="h-[18px] w-[18px] shrink-0" />
          <span>Déconnexion</span>
        </button>
      </div>
    </aside>
  );
}

function titrePage(module, pathname) {
  const item = module.menu.find((i) => pathname.startsWith(`${module.chemin}/${i.chemin}`));
  return item?.libelle ?? module.libelle;
}

export default function ModuleShell({ module, children }) {
  const [menuMobile, setMenuMobile] = useState(false);
  const { pathname } = useLocation();
  const page = titrePage(module, pathname);

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-canvas text-foreground" style={styleModule(module)}>
      <div className="hidden md:flex md:shrink-0">
        <ModuleSidebar module={module} />
      </div>

      {menuMobile && (
        <div className="fixed inset-0 z-50 flex animate-in fade-in duration-200 md:hidden">
          <div className="fixed inset-0 bg-black/40 backdrop-blur-sm" onClick={() => setMenuMobile(false)} />
          <div className="relative flex h-full w-auto max-w-xs animate-in slide-in-from-left duration-200">
            <ModuleSidebar module={module} onNavigate={() => setMenuMobile(false)} />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-border/70 bg-background/80 px-4 backdrop-blur-md md:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <button
              type="button"
              onClick={() => setMenuMobile(true)}
              className="-ml-2 rounded-md p-2 text-muted-foreground hover:bg-muted focus:outline-none md:hidden"
              aria-label="Ouvrir le menu de navigation"
            >
              <Menu className="h-5 w-5" />
            </button>
            <nav aria-label="Fil d’Ariane" className="flex min-w-0 items-center gap-1.5 text-sm">
              <span className="hidden items-center gap-2 text-muted-foreground sm:flex">
                <span aria-hidden className="size-2 rounded-full bg-module" />
                {module.libelle}
              </span>
              {page !== module.libelle && (
                <>
                  <ChevronRight className="hidden size-4 text-muted-foreground/60 sm:block" />
                  <h2 className="truncate font-semibold tracking-tight text-foreground">{page}</h2>
                </>
              )}
              {page === module.libelle && <h2 className="truncate font-semibold tracking-tight text-foreground sm:hidden">{page}</h2>}
            </nav>
          </div>
          <MenuUtilisateur />
        </header>
        <main className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-[1440px] p-4 md:p-8">
            {children ?? <Outlet />}
          </div>
        </main>
      </div>

      <Toaster />
      <ConfirmDialogHost />
    </div>
  );
}
