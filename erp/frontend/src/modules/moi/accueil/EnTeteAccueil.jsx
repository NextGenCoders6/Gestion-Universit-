/** En-tête de l'accueil : salutation selon l'heure et date du jour en toutes lettres. */
import { dateLongue, salutation } from '@/lib/dates';

export default function EnTeteAccueil({ nomComplet }) {
  const maintenant = new Date();
  return (
    <header className="space-y-1">
      <p className="text-sm font-medium text-muted-foreground">{dateLongue(maintenant)}</p>
      <h1 className="text-[26px] font-semibold leading-tight tracking-tight text-foreground text-balance">
        {`${salutation(maintenant)}, ${nomComplet ?? ''}`}
      </h1>
    </header>
  );
}
