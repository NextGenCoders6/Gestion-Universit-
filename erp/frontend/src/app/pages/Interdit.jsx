import { Link } from 'react-router-dom';
import { AlertCircle } from '@/components/ui/icons';

export default function Interdit() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <AlertCircle className="size-10 text-destructive" />
      <h3 className="text-lg font-semibold text-foreground">Accès non autorisé</h3>
      <p className="max-w-md text-sm text-muted-foreground">
        Vous n’avez pas les droits nécessaires pour ouvrir cette page. Contactez l’administrateur si besoin.
      </p>
      <Link to="/" className="text-sm font-medium text-primary hover:underline">Retour aux modules</Link>
    </div>
  );
}
