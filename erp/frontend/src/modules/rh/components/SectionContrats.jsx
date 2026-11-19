/** Contrats d'une personne : historique, nouveau contrat (renouvellement), fin de contrat. */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Plus } from '@/components/ui/icons';
import Champ from '@/components/shared/Champ';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import { useToast } from '@/hooks/use-toast';
import { confirmer } from '@/lib/confirmer';
import { erreursServeur, messageErreur } from '@/lib/erreurs';
import * as api from '../api';
import { useEstResponsableRH } from '../hooks';
import { dateFr, ETATS_CONTRAT, montant, TYPES_CONTRAT } from '../lib/format';
import { CHAMPS_CONTRAT, contratDepuis } from '../lib/contrat';
import ChampsContrat from './ChampsContrat';
import Pastille from '@/components/shared/Pastille';

function NouveauContrat({ personne, types, onFermer }) {
  const client = useQueryClient();
  const { toast } = useToast();
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const form = useForm({ defaultValues: Object.fromEntries(CHAMPS_CONTRAT.map((c) => [c, ''])) });
  const creer = useMutation({
    mutationFn: (v) => api.creerContrat({ personne, ...contratDepuis(v) }),
    onSuccess: () => { client.invalidateQueries({ queryKey: ['rh'] }); toast({ title: 'Contrat enregistré' }); onFermer(); },
    onError: (e) => setErreurs(erreursServeur(e, CHAMPS_CONTRAT)),
  });
  const erreur = (n) => erreurs.champs[n] ?? form.formState.errors[n]?.message;
  return (
    <FormModal open onClose={onFermer} title="Nouveau contrat" onConfirm={form.handleSubmit((v) => creer.mutate(v))} isPending={creer.isPending}>
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={(e) => e.preventDefault()}>
        <ChampsContrat register={form.register} control={form.control} erreur={erreur} requis types={types} />
        <div className="sm:col-span-2"><ErreurFormulaire message={erreurs.global} /></div>
      </form>
    </FormModal>
  );
}

function FinContrat({ contrat, onFermer }) {
  const client = useQueryClient();
  const { toast } = useToast();
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const form = useForm({ defaultValues: { date_fin: new Date().toISOString().slice(0, 10) } });
  const terminer = useMutation({
    mutationFn: (v) => api.terminerContrat(contrat.id, v.date_fin),
    onSuccess: () => { client.invalidateQueries({ queryKey: ['rh'] }); toast({ title: 'Fin de contrat enregistrée' }); onFermer(); },
    onError: (e) => setErreurs(erreursServeur(e, ['date_fin'])),
  });
  return (
    <FormModal open onClose={onFermer} title="Mettre fin au contrat" confirmLabel="Terminer le contrat" isDestructive
      description="La personne n'est plus active après cette date." onConfirm={form.handleSubmit((v) => terminer.mutate(v))}
      isPending={terminer.isPending}>
      <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="date_fin" label="Dernier jour du contrat" type="date" requis register={form.register}
          erreur={erreurs.champs.date_fin ?? form.formState.errors.date_fin?.message} />
        <ErreurFormulaire message={erreurs.global} />
      </form>
    </FormModal>
  );
}

export default function SectionContrats({ personne, contrats, enseignant }) {
  const responsable = useEstResponsableRH();
  const client = useQueryClient();
  const { toast } = useToast();
  const annuler = async (c) => {
    if (!(await confirmer({ titre: 'Annuler ce contrat à venir ?', libelleConfirmer: 'Annuler le contrat', destructif: true }))) return;
    try { await api.supprimerContrat(c.id); client.invalidateQueries({ queryKey: ['rh'] }); toast({ title: 'Contrat annulé' }); }
    catch (e) { toast({ title: 'Annulation impossible', description: messageErreur(e), variant: 'destructive' }); }
  };
  const [nouveau, setNouveau] = useState(false);
  const [fin, setFin] = useState(null);
  const types = enseignant ? TYPES_CONTRAT : TYPES_CONTRAT.filter((t) => t.valeur === 'permanent');
  return (
    <section className="space-y-2 carte p-4">
      <header className="flex items-center justify-between">
        <h2 className="font-semibold">Contrats</h2>
        {responsable && <Button size="sm" variant="outline" onClick={() => setNouveau(true)}><Plus /> Nouveau contrat</Button>}
      </header>
      {contrats.length === 0 && <p className="text-sm text-muted-foreground">Aucun contrat.</p>}
      <ul className="space-y-2">
        {contrats.map((c) => (
          <li key={c.id} className="flex flex-wrap items-center justify-between gap-2 rounded-md bg-muted/40 px-3 py-2 text-sm">
            <div>
              <div className="font-medium">
                {c.type === 'permanent' ? 'Permanent' : 'Vacataire'} · {dateFr(c.date_debut)} → {c.date_fin ? dateFr(c.date_fin) : 'durée indéterminée'}
              </div>
              <div className="text-xs text-muted-foreground">
                {c.type === 'permanent' ? `${montant(c.salaire_mensuel)} / mois` : `${montant(c.taux_horaire)} / heure`}
                {c.rib && ` · RIB ${c.rib}`}{c.numero_secu && ` · Sécu ${c.numero_secu}`}{c.diplome && ` · ${c.diplome}`}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Pastille ton={{ en_cours: 'vert', a_venir: 'bleu' }[c.etat] ?? 'gris'}>{ETATS_CONTRAT[c.etat]}</Pastille>
              {responsable && c.etat === 'en_cours' && (
                <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setFin(c)}>Terminer</Button>
              )}
              {responsable && c.etat === 'a_venir' && (
                <Button size="sm" variant="ghost" className="text-destructive" onClick={() => annuler(c)}>Annuler le contrat</Button>
              )}
            </div>
          </li>
        ))}
      </ul>
      {nouveau && <NouveauContrat personne={personne} types={types} onFermer={() => setNouveau(false)} />}
      {fin && <FinContrat contrat={fin} onFermer={() => setFin(null)} />}
    </section>
  );
}
