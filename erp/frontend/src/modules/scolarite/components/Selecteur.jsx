/** Liste déroulante de sélection (classe, EC, semestre…) partagée par les écrans de la Scolarité. */
import { Label } from '@/components/ui/label';

const CLASSE = 'flex h-9 w-full rounded-md border border-border bg-background px-3 py-1 text-sm shadow-xs '
  + 'outline-none focus-visible:ring-2 focus-visible:ring-ring';

export default function Selecteur({ id, label, valeur, onChange, options, vide = 'Choisir…', className = '' }) {
  return (
    <div className={`space-y-1.5 ${className}`}>
      <Label htmlFor={id}>{label}</Label>
      <select id={id} className={CLASSE} value={valeur} onChange={(e) => onChange(e.target.value)}>
        <option value="">{vide}</option>
        {options.map((o) => <option key={o.valeur} value={o.valeur}>{o.libelle}</option>)}
      </select>
    </div>
  );
}
