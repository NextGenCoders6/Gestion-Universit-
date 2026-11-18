/** Création d'un étudiant et de sa première inscription, en un seul formulaire. */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Champ from '@/components/shared/Champ';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import { useToast } from '@/hooks/use-toast';
import * as api from '../api';
import { useClasses } from '../hooks';
import { erreursEtudiant } from '../lib/erreurs';

const CHAMPS = ['nom', 'prenom', 'genre', 'date_naissance', 'lieu_naissance', 'email', 'telephone', 'classe', 'date_inscription'];

export default function NouvelEtudiantDialog({ onFermer, onCree }) {
  const client = useQueryClient();
  const { toast } = useToast();
  const classes = useClasses();
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const form = useForm({ defaultValues: Object.fromEntries(CHAMPS.map((c) => [c, ''])) });
  const creer = useMutation({
    mutationFn: (v) => api.creerEtudiant({
      personne: { nom: v.nom, prenom: v.prenom, genre: v.genre, date_naissance: v.date_naissance || null,
        lieu_naissance: v.lieu_naissance, email: v.email, telephone: v.telephone },
      classe: Number(v.classe) || null,
      ...(v.date_inscription ? { date_inscription: v.date_inscription } : {}),
    }),
    onSuccess: (etudiant) => {
      client.invalidateQueries({ queryKey: ['scolarite'] });
      toast({ title: 'Étudiant inscrit', description: `Matricule ${etudiant.matricule}` });
      onCree(etudiant);
    },
    onError: (e) => setErreurs(erreursEtudiant(e, CHAMPS)),
  });
  const erreur = (n) => erreurs.champs[n] ?? form.formState.errors[n]?.message;
  const classesOuvertes = (classes.data ?? []).filter((c) => !c.archivee);

  return (
    <FormModal open onClose={onFermer} title="Nouvel étudiant" confirmLabel="Inscrire"
      description="L'e-mail et la date de naissance servent à l'étudiant pour activer son compte."
      onConfirm={form.handleSubmit((v) => creer.mutate(v))} isPending={creer.isPending}>
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="nom" label="Nom" requis register={form.register} erreur={erreur('nom')} />
        <Champ nom="prenom" label="Prénom" requis register={form.register} erreur={erreur('prenom')} />
        <Champ nom="genre" label="Genre" type="select" requis register={form.register} erreur={erreur('genre')}
          options={[{ valeur: 'F', libelle: 'Féminin' }, { valeur: 'M', libelle: 'Masculin' }]} />
        <Champ nom="date_naissance" label="Date de naissance" type="date" requis register={form.register} erreur={erreur('date_naissance')} />
        <Champ nom="lieu_naissance" label="Lieu de naissance" register={form.register} erreur={erreur('lieu_naissance')} />
        <Champ nom="email" label="E-mail" type="email" requis register={form.register} erreur={erreur('email')} />
        <Champ nom="telephone" label="Téléphone" register={form.register} erreur={erreur('telephone')} />
        <Champ nom="classe" label="Classe" type="select" requis register={form.register} erreur={erreur('classe')}
          options={classesOuvertes.map((c) => ({ valeur: String(c.id), libelle: c.libelle }))} />
        <Champ nom="date_inscription" label="Date d'inscription" type="date" register={form.register}
          erreur={erreur('date_inscription')} aide="Aujourd'hui si vide." />
        <div className="sm:col-span-2"><ErreurFormulaire message={erreurs.global} /></div>
      </form>
    </FormModal>
  );
}
