import { Link } from 'react-router-dom';
import { UserCircle } from '@/components/ui/icons';

/** Espace personnel étudiant / enseignant : rempli par les phases EDT et Scolarité. */
export default function MonEspace() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
      <UserCircle className="size-10 text-muted-foreground" />
      <h3 className="text-lg font-semibold text-foreground">Mon espace</h3>
      <p className="max-w-md text-sm text-muted-foreground">
        Votre planning, vos notes et vos documents arriveront ici dans une prochaine version.
      </p>
      <Link to="/" className="text-sm font-medium text-primary hover:underline">Retour aux modules</Link>
    </div>
  );
}
