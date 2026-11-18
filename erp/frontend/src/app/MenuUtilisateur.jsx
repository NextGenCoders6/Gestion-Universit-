import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { LogOut } from '@/components/ui/icons';
import { logout } from '@/api/auth';
import useAuthStore from '@/store/authStore';

function initiales(nom = '') {
  return nom.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase();
}

/** Nom, avatar et menu de déconnexion — repris de la barre supérieure de l'EDT. */
export default function MenuUtilisateur() {
  const user = useAuthStore((state) => state.user);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          className="flex items-center gap-3 rounded-lg px-3 py-2 text-right transition-colors hover:bg-muted/50 focus:outline-none"
        >
          <span className="hidden text-sm font-semibold leading-tight text-foreground sm:block">{user?.nom_complet}</span>
          <Avatar className="h-9 w-9">
            {user?.photo && <AvatarImage src={user.photo} alt="" className="object-cover" />}
            <AvatarFallback className="bg-primary/10 text-sm font-semibold text-primary">
              {initiales(user?.nom_complet)}
            </AvatarFallback>
          </Avatar>
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="truncate">{user?.username}</DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={() => logout()} className="text-destructive focus:text-destructive">
          <LogOut className="h-4 w-4" /> Déconnexion
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
