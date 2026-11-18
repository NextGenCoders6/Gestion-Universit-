/** Dialogues d'écriture de la Finance : paiement, montant, motif d'annulation. */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import Champ from '@/components/shared/Champ';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import { erreursServeur } from '@/lib/erreurs';
import { fcfa, MODES } from '../lib/format';

function useEnvoi(envoyer, champs, onFini) {
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const [enCours, setEnCours] = useState(false);
  const soumettre = async (v) => {
    setEnCours(true);
    setErreurs({ champs: {}, global: null });
    try { await envoyer(v); onFini(); } catch (e) { setErreurs(erreursServeur(e, champs)); } finally { setEnCours(false); }
  };
  return { erreurs, enCours, soumettre };
}

export function PaiementDialog({ titre, reste, libelleBouton = 'Encaisser', envoyer, onFermer }) {
  const form = useForm({ defaultValues: { montant: '', mode: '', date: '', reference: '' } });
  const { erreurs, enCours, soumettre } = useEnvoi(envoyer, ['montant', 'mode', 'date', 'reference'], onFermer);
  const erreur = (n) => erreurs.champs[n] ?? form.formState.errors[n]?.message;
  return (
    <FormModal open onClose={onFermer} title={titre} description={`Reste à payer : ${fcfa(reste)}`} confirmLabel={libelleBouton}
      onConfirm={form.handleSubmit(soumettre)} isPending={enCours}>
      <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="montant" label="Montant (FCFA)" type="number" requis register={form.register} erreur={erreur('montant')} />
        <Champ nom="mode" label="Mode de paiement" type="select" requis register={form.register} erreur={erreur('mode')} options={MODES} />
        <Champ nom="date" label="Date du paiement" type="date" register={form.register} erreur={erreur('date')} aide="Aujourd’hui si vide." />
        <Champ nom="reference" label="Référence (n° de transaction, de chèque…)" register={form.register} erreur={erreur('reference')} />
        <ErreurFormulaire message={erreurs.global} />
      </form>
    </FormModal>
  );
}

export function MontantDialog({ titre, description, valeur, envoyer, onFermer }) {
  const form = useForm({ defaultValues: { montant: valeur ?? '' } });
  const { erreurs, enCours, soumettre } = useEnvoi((v) => envoyer(v.montant), ['montant'], onFermer);
  return (
    <FormModal open onClose={onFermer} title={titre} description={description} onConfirm={form.handleSubmit(soumettre)} isPending={enCours}>
      <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="montant" label="Montant (FCFA)" type="number" requis register={form.register}
          erreur={erreurs.champs.montant ?? form.formState.errors.montant?.message} />
        <ErreurFormulaire message={erreurs.global} />
      </form>
    </FormModal>
  );
}

export function MotifDialog({ titre, description, libelleBouton = 'Annuler le paiement', envoyer, onFermer }) {
  const form = useForm({ defaultValues: { motif: '' } });
  const { erreurs, enCours, soumettre } = useEnvoi((v) => envoyer(v.motif.trim()), ['motif'], onFermer);
  return (
    <FormModal open onClose={onFermer} title={titre} description={description} confirmLabel={libelleBouton} isDestructive
      onConfirm={form.handleSubmit(soumettre)} isPending={enCours}>
      <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="motif" label="Motif" type="textarea" requis register={form.register}
          erreur={erreurs.champs.motif ?? form.formState.errors.motif?.message} />
        <ErreurFormulaire message={erreurs.global} />
      </form>
    </FormModal>
  );
}
