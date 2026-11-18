import { Link } from 'react-router-dom';

export default function Introuvable() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
      <h3 className="text-lg font-semibold text-foreground">404 — Page introuvable</h3>
      <Link to="/" className="text-sm font-medium text-primary hover:underline">Retour aux modules</Link>
    </div>
  );
}
