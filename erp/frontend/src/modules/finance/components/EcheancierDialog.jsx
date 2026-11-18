/** Adaptation de l'échéancier d'un dossier : la somme doit rester égale au montant dû. */
import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Plus, Trash2 } from '@/components/ui/icons';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import { erreursServeur } from '@/lib/erreurs';
import { fcfa } from '../lib/format';

export default function EcheancierDialog({ dossier, envoyer, onFermer }) {
  const [lignes, setLignes] = useState(dossier.echeances.map(({ mois, date_limite, montant }) => ({ mois, date_limite: String(date_limite), montant: String(montant) })));
  const [erreur, setErreur] = useState(null);
  const [enCours, setEnCours] = useState(false);
  const total = lignes.reduce((s, l) => s + (Number(l.montant) || 0), 0);
  const changer = (i, champ, v) => setLignes((ls) => ls.map((l, j) => (j === i ? { ...l, [champ]: v } : l)));
  const valider = async () => {
    if (total !== dossier.montant_du) { setErreur(`La somme (${fcfa(total)}) doit égaler le montant dû (${fcfa(dossier.montant_du)}).`); return; }
    setEnCours(true);
    try { await envoyer(lignes); onFermer(); } catch (e) { setErreur(erreursServeur(e).global ?? 'Échéancier refusé.'); } finally { setEnCours(false); }
  };
  return (
    <FormModal open onClose={onFermer} title="Adapter l’échéancier" description={`Montant dû : ${fcfa(dossier.montant_du)}`}
      onConfirm={valider} isPending={enCours}>
      <div className="space-y-2">
        {lignes.map((l, i) => (
          <div key={i} className="grid grid-cols-[1fr_1fr_1fr_auto] gap-2">
            <Input aria-label={`Mois ${i + 1}`} value={l.mois} onChange={(e) => changer(i, 'mois', e.target.value)} placeholder="AAAA-MM" />
            <Input aria-label={`Date limite ${i + 1}`} type="date" value={l.date_limite} onChange={(e) => changer(i, 'date_limite', e.target.value)} />
            <Input aria-label={`Montant ${i + 1}`} type="number" value={l.montant} onChange={(e) => changer(i, 'montant', e.target.value)} />
            <Button variant="ghost" size="icon" aria-label={`Supprimer la mensualité ${i + 1}`} onClick={() => setLignes((ls) => ls.filter((_, j) => j !== i))}><Trash2 /></Button>
          </div>
        ))}
        <div className="flex items-center justify-between text-sm">
          <Button variant="outline" size="sm" onClick={() => setLignes((ls) => [...ls, { mois: '', date_limite: '', montant: '' }])}><Plus /> Mensualité</Button>
          <span className={total === dossier.montant_du ? 'text-primary' : 'text-destructive'}>Total : {fcfa(total)}</span>
        </div>
        <ErreurFormulaire message={erreur} />
      </div>
    </FormModal>
  );
}
