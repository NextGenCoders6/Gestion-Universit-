/** Vacations des vacataires de la faculté : confirmation des heures retenues, retrait, historique. */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import Champ from '@/components/shared/Champ';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import { TableHistorique, TableVacations } from '@/modules/rh/components/TablesVacations';
import { heures, montant } from '@/modules/rh/lib/format';
import SelecteurAnnee from '@/modules/rh/components/SelecteurAnnee';
import * as api from '../api';

const ONGLETS = [['a_confirmer', 'À confirmer'], ['en_cours', 'En cours'], ['confirmee', 'Confirmées'], ['historique', 'Historique']];

function ConfirmerDialog({ ligne, onFermer }) {
  const client = useQueryClient();
  const { toast } = useToast();
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const form = useForm({ defaultValues: { heures_retenues: ligne.heures_dues, motif: '' } });
  const confirmer = useMutation({
    mutationFn: (v) => api.confirmerVacation(ligne.affectation, { heures_retenues: String(v.heures_retenues), motif: v.motif.trim() }),
    onSuccess: (r) => {
      client.invalidateQueries({ queryKey: ['scolarite', 'vacations'] });
      toast({ title: 'Vacation confirmée', description: `${ligne.enseignant_nom} · ${montant(r.vacation?.montant)}` });
      onFermer();
    },
    onError: (e) => setErreurs(erreursServeur(e, ['heures_retenues', 'motif'])),
  });
  const valider = (v) => {
    const change = Number(v.heures_retenues) !== Number(ligne.heures_dues);
    if (!v.motif.trim() && (change || !ligne.terminee)) {
      form.setError('motif', { message: change ? 'Indiquez le motif : les heures retenues diffèrent des heures dues.'
        : "Indiquez le motif : l'affectation n'est pas terminée." });
      return;
    }
    confirmer.mutate(v);
  };
  const erreur = (n) => erreurs.champs[n] ?? form.formState.errors[n]?.message;
  return (
    <FormModal open onClose={onFermer} title={`Vacation — ${ligne.enseignant_nom}`} confirmLabel="Confirmer la vacation"
      description={`${ligne.ec_code} · ${ligne.classe_libelle} · ${heures(ligne.heures_effectuees)} faites sur ${heures(ligne.heures_prevues)} prévues, taux ${montant(ligne.taux_horaire)} / h.`}
      onConfirm={form.handleSubmit(valider)} isPending={confirmer.isPending}>
      <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="heures_retenues" label="Heures retenues" type="number" requis register={form.register} erreur={erreur('heures_retenues')}
          aide={`Heures dues : ${heures(ligne.heures_dues)}${ligne.heures_jumelles ? ` (${heures(ligne.heures_jumelles)} de cours mutualisés déjà comptées sur l’autre classe)` : ''}.`} />
        <Champ nom="motif" label="Motif" type="textarea" register={form.register} erreur={erreur('motif')}
          aide="Obligatoire si les heures changent ou si l’affectation n’est pas terminée." />
        <ErreurFormulaire message={erreurs.global} />
      </form>
    </FormModal>
  );
}

function RetirerDialog({ ligne, onFermer }) {
  const client = useQueryClient();
  const { toast } = useToast();
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const form = useForm({ defaultValues: { motif: '' } });
  const retirer = useMutation({
    mutationFn: (v) => api.retirerVacation(ligne.affectation, v.motif.trim()),
    onSuccess: () => { client.invalidateQueries({ queryKey: ['scolarite', 'vacations'] }); toast({ title: 'Confirmation retirée' }); onFermer(); },
    onError: (e) => setErreurs(erreursServeur(e, ['motif'])),
  });
  return (
    <FormModal open onClose={onFermer} title="Retirer la confirmation ?" confirmLabel="Retirer la confirmation" isDestructive
      description={`${ligne.enseignant_nom} · ${ligne.ec_code} · ${montant(ligne.vacation?.montant)}`}
      onConfirm={form.handleSubmit((v) => retirer.mutate(v))} isPending={retirer.isPending}>
      <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="motif" label="Motif" type="textarea" requis register={form.register}
          erreur={erreurs.champs.motif ?? form.formState.errors.motif?.message} />
        <ErreurFormulaire message={erreurs.global} />
      </form>
    </FormModal>
  );
}

export default function Vacations() {
  const [onglet, setOnglet] = useState('a_confirmer');
  const [annee, setAnnee] = useState('');
  const filtreAnnee = annee ? { annee } : {};
  const [confirmation, setConfirmation] = useState(null);
  const [retrait, setRetrait] = useState(null);
  const lignes = useQuery({ queryKey: ['scolarite', 'vacations', onglet, annee], queryFn: () => api.listerVacations({ etat: onglet, ...filtreAnnee }),
    enabled: onglet !== 'historique' });
  const historique = useQuery({ queryKey: ['scolarite', 'vacations', 'historique'], queryFn: () => api.historiqueVacations(),
    enabled: onglet === 'historique' });
  const actions = (l) => {
    if (l.vacation) return <Button size="sm" variant="ghost" className="text-destructive" onClick={() => setRetrait(l)}>Retirer</Button>;
    if (!l.confirmable) return null;
    return <Button size="sm" variant={l.terminee ? 'default' : 'outline'} onClick={() => setConfirmation(l)}>Confirmer</Button>;
  };
  return (
    <div className="space-y-4">
      <PageHeader titre="Vacations"
        description="Un vacataire est payé quand il termine son volume : confirmez les heures retenues, la Finance réglera la vacation." />
      <SelecteurAnnee lister={api.listerAnnees} valeur={annee} onChange={setAnnee} />
      <Tabs value={onglet} onValueChange={setOnglet}>
        <TabsList>{ONGLETS.map(([v, l]) => <TabsTrigger key={v} value={v}>{l}</TabsTrigger>)}</TabsList>
      </Tabs>
      {onglet === 'historique'
        ? <TableHistorique lignes={historique.data ?? []} />
        : lignes.isLoading ? <p className="text-sm text-muted-foreground">Chargement…</p>
          : <TableVacations lignes={lignes.data ?? []} actions={actions} />}
      {confirmation && <ConfirmerDialog ligne={confirmation} onFermer={() => setConfirmation(null)} />}
      {retrait && <RetirerDialog ligne={retrait} onFermer={() => setRetrait(null)} />}
    </div>
  );
}
