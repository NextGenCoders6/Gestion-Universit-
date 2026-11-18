/** Paie des enseignants ou du personnel : génération du mois, paiements, reçus, ajustements. */
import { useState } from 'react';
import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Printer } from '@/components/ui/icons';
import PageHeader from '@/components/shared/PageHeader';
import Selecteur from '@/components/shared/Selecteur';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import { BadgeStatut } from '../components/Badges';
import { MontantDialog, MotifDialog, PaiementDialog } from '../components/Dialogues';
import { useEstResponsableFinance } from '../hooks';
import { dateFr, fcfa, moisCourant, STATUTS_PAIE } from '../lib/format';

function Paiements({ ligne, responsable, onAnnuler }) {
  const { toast } = useToast();
  const detail = useQuery({ queryKey: ['finance', 'ligne-paie', ligne.id], queryFn: () => api.lignePaie(ligne.id) });
  const recu = async (p) => {
    try { await api.telecharger(`/finance/paiements-paie/${p.id}/recu.pdf`, `recu-${p.numero}.pdf`); } catch (e) {
      toast({ title: 'Reçu indisponible', description: erreursServeur(e).global, variant: 'destructive' });
    }
  };
  return (
    <ul className="space-y-1 py-1">{(detail.data?.paiements ?? []).map((p) => (
      <li key={p.id} className={`flex items-center justify-between gap-2 text-xs ${p.annule ? 'text-muted-foreground line-through' : ''}`}>
        <span>{dateFr(p.date)} · {fcfa(p.montant)} · {p.mode_libelle} · {p.numero}</span>
        <span className="flex gap-1">
          <Button size="xs" variant="ghost" onClick={() => recu(p)}><Printer /> Reçu</Button>
          {responsable && !p.annule && <Button size="xs" variant="ghost" className="text-destructive" onClick={() => onAnnuler(p)}>Annuler</Button>}
        </span>
      </li>))}</ul>
  );
}

export default function Paie({ role, titre }) {
  const client = useQueryClient();
  const { toast } = useToast();
  const responsable = useEstResponsableFinance();
  const [mois, setMois] = useState(moisCourant());
  const [filtre, setFiltre] = useState({ origine: '', statut: '' });
  const [dialogue, setDialogue] = useState(null);
  const [ouverte, setOuverte] = useState(null);
  // Les salaires du mois choisi, et toujours toutes les vacations (sans mois) : aucune ne disparaît de la liste.
  const parMois = !/^\d{4}-\d{2}$/.test(mois) ? {}
    : filtre.origine === 'salaire' ? { mois, origine: 'salaire' } : { mois, avec_vacations: 'true' };
  const requete = { role, page_size: 200, ...(filtre.origine === 'vacation' ? { origine: 'vacation' } : parMois),
    ...(filtre.statut ? { statut: filtre.statut } : {}) };
  const liste = useQuery({ queryKey: ['finance', 'paie', requete], queryFn: () => api.listerPaie(requete), placeholderData: keepPreviousData });
  const rafraichir = () => client.invalidateQueries({ queryKey: ['finance'] });
  const generer = async () => {
    try {
      const r = await api.genererPaie(mois);
      rafraichir();
      toast({ title: `Paie de ${r.mois}`, description: `${r.creees} ligne(s) créée(s), ${r.existantes} déjà présente(s).` });
    } catch (e) { toast({ title: 'Génération impossible', description: erreursServeur(e).global, variant: 'destructive' }); }
  };
  const lignes = liste.data?.results ?? [];
  return (
    <div className="space-y-4">
      <PageHeader titre={titre} description="Salaires mensuels des permanents et vacations confirmées par la faculté." />
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex items-end gap-2">
          <div className="space-y-1.5"><Label htmlFor="mois">Mois</Label><Input id="mois" type="month" value={mois} onChange={(e) => setMois(e.target.value)} className="w-44" /></div>
          {responsable && <Button onClick={generer} disabled={!/^\d{4}-\d{2}$/.test(mois)}>Générer la paie</Button>}
        </div>
        <Selecteur id="origine" label="Origine" vide="Toutes" valeur={filtre.origine} className="w-44"
          options={[{ valeur: 'salaire', libelle: 'Salaires' }, { valeur: 'vacation', libelle: 'Vacations' }]} onChange={(v) => setFiltre((f) => ({ ...f, origine: v }))} />
        <Selecteur id="statut" label="Statut" vide="Tous" valeur={filtre.statut} className="w-44"
          options={Object.entries(STATUTS_PAIE).map(([valeur, libelle]) => ({ valeur, libelle }))} onChange={(v) => setFiltre((f) => ({ ...f, statut: v }))} />
      </div>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-xs uppercase text-muted-foreground"><tr>
            <th className="px-3 py-2 text-left">Bénéficiaire</th><th className="px-3 py-2 text-left">Objet</th><th className="px-2 py-2">Payé / dû</th><th className="px-2 py-2">Statut</th><th className="px-2 py-2" />
          </tr></thead>
          <tbody>
            {lignes.length === 0 && <tr><td colSpan={5} className="px-3 py-8 text-center text-muted-foreground">Aucune ligne de paie.</td></tr>}
            {lignes.map((l) => [
              <tr key={l.id} className="border-t border-border">
                <td className="px-3 py-1.5 font-medium">{l.nom_complet}</td>
                <td className="px-3 py-1.5">{l.origine === 'salaire' ? `Salaire ${l.mois}` : l.libelle.replace(/^Vacation — [^,]+, /, 'Vacation — ')}</td>
                <td className="px-2 py-1.5 text-center">{fcfa(l.montant_paye)} / {fcfa(l.montant_du)}</td>
                <td className="px-2 py-1.5 text-center"><BadgeStatut libelle={STATUTS_PAIE[l.statut]} ok={l.statut === 'paye'} /></td>
                <td className="px-2 py-1.5 text-right whitespace-nowrap">
                  <Button size="sm" variant="ghost" onClick={() => setOuverte(ouverte === l.id ? null : l.id)}>Paiements</Button>
                  {responsable && l.reste > 0 && <Button size="sm" onClick={() => setDialogue({ payer: l })}>Payer</Button>}
                  {responsable && l.montant_paye <= 0 && <Button size="sm" variant="ghost" onClick={() => setDialogue({ ajuster: l })}>Ajuster</Button>}
                </td>
              </tr>,
              ouverte === l.id && <tr key={`p-${l.id}`}><td colSpan={5} className="bg-muted/20 px-6"><Paiements ligne={l} responsable={responsable} onAnnuler={(p) => setDialogue({ annuler: p })} /></td></tr>,
            ])}
          </tbody>
        </table>
      </div>
      {dialogue?.payer && (
        <PaiementDialog titre={`Payer — ${dialogue.payer.nom_complet}`} reste={dialogue.payer.reste} libelleBouton="Payer" onFermer={() => setDialogue(null)}
          envoyer={async (v) => {
            const r = await api.payer(dialogue.payer.id, { montant: v.montant, mode: v.mode, date: v.date || null, reference: v.reference });
            rafraichir();
            toast({ title: 'Paiement enregistré', description: `${fcfa(r.paiement.montant)} · ${r.paiement.numero}` });
          }} />
      )}
      {dialogue?.ajuster && (
        <MontantDialog titre="Ajuster le montant dû" valeur={dialogue.ajuster.montant_du} onFermer={() => setDialogue(null)}
          description="Possible tant qu’aucun paiement n’est enregistré."
          envoyer={async (m) => { await api.ajusterPaie(dialogue.ajuster.id, m); rafraichir(); toast({ title: 'Montant ajusté' }); }} />
      )}
      {dialogue?.annuler && (
        <MotifDialog titre="Annuler ce paiement ?" description={`${fcfa(dialogue.annuler.montant)} du ${dateFr(dialogue.annuler.date)}`} onFermer={() => setDialogue(null)}
          envoyer={async (motif) => { await api.annulerPaiementPaie(dialogue.annuler.id, motif); rafraichir(); toast({ title: 'Paiement annulé' }); }} />
      )}
    </div>
  );
}
