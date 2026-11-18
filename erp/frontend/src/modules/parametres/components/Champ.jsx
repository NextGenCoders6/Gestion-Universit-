import { useId } from 'react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

const CLASSE_SELECT =
  'flex h-9 w-full rounded-md border border-border bg-background px-3 py-1 text-sm shadow-xs outline-none ' +
  'focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50';

/**
 * Un champ de formulaire : libellé, contrôle, erreur sous le champ.
 * type : 'text' | 'email' | 'password' | 'number' | 'date' | 'textarea' | 'select' | 'checkbox'
 * options (select) : [{ valeur, libelle }]
 * `register` vient de react-hook-form.
 */
export default function Champ({ nom, label, type = 'text', options = [], register, erreur, requis, vide = '—', aide }) {
  const id = useId();
  const enregistrement = register(nom, requis ? { required: 'Ce champ est obligatoire.' } : {});

  let controle;
  if (type === 'select') {
    controle = (
      <select id={id} className={CLASSE_SELECT} {...enregistrement}>
        <option value="">{vide}</option>
        {options.map((o) => <option key={o.valeur} value={o.valeur}>{o.libelle}</option>)}
      </select>
    );
  } else if (type === 'textarea') {
    controle = <textarea id={id} rows={3} className={cn(CLASSE_SELECT, 'h-auto py-2')} {...enregistrement} />;
  } else if (type === 'checkbox') {
    controle = <input id={id} type="checkbox" className="size-4 accent-primary" {...enregistrement} />;
  } else {
    controle = <Input id={id} type={type} {...enregistrement} />;
  }

  return (
    <div data-champ={nom} className={cn('space-y-1.5', type === 'checkbox' && 'flex items-center gap-2 space-y-0')}>
      <div className="flex items-center gap-1">
        <Label htmlFor={id}>{label}</Label>
        {requis && <span aria-hidden="true" className="text-sm text-destructive">*</span>}
      </div>
      {controle}
      {aide && !erreur && <p className="text-xs text-muted-foreground">{aide}</p>}
      {erreur && <p className="text-xs font-medium text-destructive">{erreur}</p>}
    </div>
  );
}
