/** Petit dialogue de formulaire partagé par les écrans de la Logistique. */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import Champ from '@/components/shared/Champ';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import { erreursServeur } from '@/lib/erreurs';

export default function Formulaire({ titre, champs, valeurs = {}, envoyer, onFermer, enfants }) {
  const noms = champs.map((c) => c.nom);
  const form = useForm({ defaultValues: Object.fromEntries(noms.map((n) => [n, valeurs[n] ?? ''])) });
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const [enCours, setEnCours] = useState(false);
  const soumettre = async (v) => {
    setEnCours(true);
    try { await envoyer(v); onFermer(); } catch (e) { setErreurs(erreursServeur(e, noms)); } finally { setEnCours(false); }
  };
  return (
    <FormModal open onClose={onFermer} title={titre} onConfirm={form.handleSubmit(soumettre)} isPending={enCours}>
      <form className="space-y-3" onSubmit={(e) => e.preventDefault()}>
        {champs.map((c) => (
          <Champ key={c.nom} {...c} register={form.register} erreur={erreurs.champs[c.nom] ?? form.formState.errors[c.nom]?.message} />
        ))}
        {enfants?.(form)}
        <ErreurFormulaire message={erreurs.global} />
      </form>
    </FormModal>
  );
}
