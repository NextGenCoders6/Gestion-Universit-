/**
 * Layout d'un module — repris de l'AppShell de l'EDT : barre latérale propre au
 * module, barre supérieure, zone de contenu, toasts et confirmations.
 */
import { useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { ConfirmDialogHost } from '@/components/shared/ConfirmDialog';
import { LayoutGrid, LogOut, Menu } from '@/components/ui/icons';
import logoUccb from '@/assets/login/logo-uccb.svg';
import { logout } from '@/api/auth';
import useAuthStore, { niveauxModule } from '@/store/authStore';
import MenuUtilisateur from './MenuUtilisateur';
import { menuVisible } from './modules';

function ModuleSidebar({ module, onNavigate }) {
  const niveaux = useAuthStore((state) => niveauxModule(state, module.code));
  const items = menuVisible(module, niveaux);

  return (
    <aside className="flex h-full w-[240px] select-none flex-col border-r border-border bg-background">
      <div className="flex h-14 items-center gap-3 border-b border-border px-4">
        <img src={logoUccb} alt="" className="size-9 shrink-0" />
        <div className="min-w-0">
          <h1 className="text-base font-bold tracking-tight text-foreground">UCCB</h1>
          <p className="truncate text-[11px] text-muted-foreground">{module.libelle}</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto p-4">
        <Link
          to="/"
          onClick={onNavigate}
          aria-label="Retour aux modules"
          className="mb-4 flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
        >
          <LayoutGrid className="h-4 w-4 shrink-0" />
          <span>Tous les modules</span>
        </Link>
        {items.map((item) => {
          const Icone = item.icone;
          return (
            <NavLink
              key={item.chemin}
              to={`${module.chemin}/${item.chemin}`}
              onClick={onNavigate}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150 ${
                  isActive ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                }`}
            >
              {Icone && <Icone className="h-4 w-4 shrink-0" />}
              <span className="truncate">{item.libelle}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="space-y-3 border-t border-border bg-muted/20 p-4">
        <button
          type="button"
          onClick={() => logout()}
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm font-medium text-destructive transition-colors duration-150 hover:bg-destructive/10"
        >
          <LogOut className="h-4 w-4 shrink-0" />
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

  return (
    <div className="flex h-dvh w-full overflow-hidden bg-muted/40 text-foreground">
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
        <header className="sticky top-0 z-40 flex h-14 w-full items-center justify-between border-b border-border bg-background px-4 md:px-6">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setMenuMobile(true)}
              className="-ml-2 rounded-md p-2 text-muted-foreground hover:bg-muted/80 focus:outline-none md:hidden"
              aria-label="Ouvrir le menu de navigation"
            >
              <Menu className="h-5 w-5" />
            </button>
            <h2 className="text-sm font-semibold tracking-tight text-foreground md:text-base">
              {titrePage(module, pathname)}
            </h2>
          </div>
          <MenuUtilisateur />
        </header>
        <main className="flex-1 overflow-y-auto bg-background p-4 md:p-6">
          {children ?? <Outlet />}
        </main>
      </div>

      <Toaster />
      <ConfirmDialogHost />
    </div>
  );
}
