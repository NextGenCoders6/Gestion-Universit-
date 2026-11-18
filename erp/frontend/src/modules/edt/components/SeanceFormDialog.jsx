/**
 * Création / modification d'une séance. Les classes et EC proposés sont ceux
 * du périmètre de l'utilisateur (lignes « enseignements ») ; les règles
 * (créneau, période, conflits, quotas) sont vérifiées par le serveur et ses
 * messages s'affichent sous le champ concerné.
 */
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Champ from '@/components/shared/Champ';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import { classesEtEcs, useAnnee, useEnseignants, useEnseignements } from '../hooks';

const CHAMPS = ['classe', 'ec', 'enseignant', 'type_seance', 'date_seance', 'heure_debut', 'heure_fin', 'libelle'];
const TYPES = ['CM', 'TD', 'TP'].map((t) => ({ valeur: t, libelle: t }));

function valeursInitiales(base) {
  return {
    classe: base.classe ? String(base.classe) : '',
    ec: base.ec ? String(base.ec) : '',
    enseignant: base.enseignant ? String(base.enseignant) : '',
    type_seance: base.type_seance ?? 'CM',
    date_seance: base.date_seance ?? '',
    heure_debut: base.heure_debut ?? '09:00',
    heure_fin: base.heure_fin ?? '11:00',
    libelle: base.libelle ?? '',
  };
}

/** Monté à l'ouverture (et démonté à la fermeture) : le formulaire repart toujours de zéro. */
export default function SeanceFormDialog({ seance, initial, onFermer }) {
  const client = useQueryClient();
  const { toast } = useToast();
  const annee = useAnnee();
  const enseignements = useEnseignements(annee.data ? { annee: annee.data.id } : {});
  const enseignants = useEnseignants();
  const classes = classesEtEcs(enseignements.data?.results);
  const form = useForm({ defaultValues: valeursInitiales(seance ?? initial ?? {}) });
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const classeChoisie = useWatch({ control: form.control, name: 'classe' });
  const enregistrer = useMutation({
    mutationFn: (v) => {
      const d = { ...v, classe: Number(v.classe), ec: Number(v.ec), enseignant: Number(v.enseignant) };
      return seance?.id ? api.modifierSeance(seance.id, d) : api.creerSeance(d);
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['edt'] });
      toast({ title: seance?.id ? 'Séance modifiée' : 'Séance créée en brouillon' });
      onFermer();
    },
    onError: (e) => setErreurs(erreursServeur(e, CHAMPS)),
  });

  const ecs = classes.find((c) => String(c.id) === classeChoisie)?.ecs ?? [];
  const erreur = (nom) => erreurs.champs[nom] ?? form.formState.errors[nom]?.message;

  return (
    <FormModal
      open
      onClose={onFermer}
      title={seance?.id ? 'Modifier la séance' : 'Nouvelle séance'}
      description={seance?.id ? undefined : 'La séance est créée en brouillon ; publiez-la pour la rendre visible.'}
      onConfirm={form.handleSubmit((v) => enregistrer.mutate(v))}
      isPending={enregistrer.isPending}
    >
      <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="classe" label="Classe" type="select" requis register={form.register} erreur={erreur('classe')}
          options={classes.map((c) => ({ valeur: String(c.id), libelle: c.libelle }))} />
        <Champ nom="ec" label="Élément constitutif" type="select" requis register={form.register} erreur={erreur('ec')}
          options={ecs.map((e) => ({ valeur: String(e.id), libelle: `${e.code} — ${e.libelle} (${e.semestre})` }))}
          vide={classeChoisie ? '—' : 'Choisissez d’abord la classe'} />
        <Champ nom="enseignant" label="Enseignant" type="select" requis register={form.register}
          erreur={erreur('enseignant')}
          options={(enseignants.data ?? []).map((e) => ({ valeur: String(e.id), libelle: `${e.nom_complet} (${e.departement_libelle})` }))} />
        <Champ nom="type_seance" label="Type" type="select" requis options={TYPES} register={form.register}
          erreur={erreur('type_seance')} />
        <Champ nom="date_seance" label="Date" type="date" requis register={form.register} erreur={erreur('date_seance')} />
        <div className="grid grid-cols-2 gap-3">
          <Champ nom="heure_debut" label="Début" type="time" requis register={form.register} erreur={erreur('heure_debut')} />
          <Champ nom="heure_fin" label="Fin" type="time" requis register={form.register} erreur={erreur('heure_fin')} />
        </div>
        <p className="text-xs text-muted-foreground">Créneaux : 09:00–11:00, 11:15–13:15, 14:15–16:15 (fin au plus tard 16:20).</p>
        <Champ nom="libelle" label="Intitulé (facultatif)" register={form.register} erreur={erreur('libelle')} />
        <ErreurFormulaire message={erreurs.global} />
      </form>
    </FormModal>
  );
}
