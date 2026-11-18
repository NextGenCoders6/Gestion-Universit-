/** Ajout d'un enseignant ou d'un membre du personnel, avec son premier contrat (facultatif). */
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import Champ from '@/components/shared/Champ';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import { useToast } from '@/hooks/use-toast';
import * as api from '../api';
import { useDepartements, useFacultes } from '../hooks';
import { erreursFiche } from '../lib/erreurs';
import { FONCTIONS, TYPES_CONTRAT } from '../lib/format';
import { CHAMPS_CONTRAT, contratDepuis } from '../lib/contrat';
import ChampsContrat from './ChampsContrat';

const IDENTITE = ['nom', 'prenom', 'genre', 'date_naissance', 'email', 'telephone'];

export default function NouvelleFicheDialog({ role, onFermer, onCree }) {
  const enseignant = role === 'enseignant';
  const client = useQueryClient();
  const { toast } = useToast();
  const departements = useDepartements();
  const facultes = useFacultes();
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const champsRole = enseignant ? ['departement', 'grade'] : ['fonction', 'fonction_autre', 'lieu_travail', 'faculte_rattachement'];
  const champs = [...IDENTITE, ...champsRole, ...CHAMPS_CONTRAT.map((c) => `contrat_${c}`)];
  const form = useForm({ defaultValues: Object.fromEntries(champs.map((c) => [c, ''])) });
  const fonction = useWatch({ control: form.control, name: 'fonction' });

  const creer = useMutation({
    mutationFn: (v) => {
      const personne = { nom: v.nom, prenom: v.prenom, genre: v.genre, date_naissance: v.date_naissance || null,
        email: v.email || null, telephone: v.telephone };
      const role = enseignant
        ? { departement: Number(v.departement) || null, grade: v.grade }
        : { fonction: v.fonction, fonction_autre: v.fonction_autre, lieu_travail: v.lieu_travail,
            faculte_rattachement: Number(v.faculte_rattachement) || null };
      const contrat = contratDepuis(v, 'contrat_');
      const d = { personne, ...role, ...(contrat ? { contrat } : {}) };
      return enseignant ? api.creerEnseignant(d) : api.creerEmploye(d);
    },
    onSuccess: (fiche) => {
      client.invalidateQueries({ queryKey: ['rh'] });
      toast({ title: enseignant ? 'Enseignant ajouté' : 'Membre du personnel ajouté', description: `Matricule ${fiche.matricule}` });
      onCree(fiche);
    },
    onError: (e) => setErreurs(erreursFiche(e, champs)),
  });
  const erreur = (n) => erreurs.champs[n] ?? form.formState.errors[n]?.message;
  const r = form.register;

  return (
    <FormModal open onClose={onFermer} title={enseignant ? 'Nouvel enseignant' : 'Nouveau membre du personnel'}
      onConfirm={form.handleSubmit((v) => creer.mutate(v))} isPending={creer.isPending}>
      <form className="grid gap-3 sm:grid-cols-2" onSubmit={(e) => e.preventDefault()}>
        <Champ nom="nom" label="Nom" requis register={r} erreur={erreur('nom')} />
        <Champ nom="prenom" label="Prénom" requis register={r} erreur={erreur('prenom')} />
        <Champ nom="genre" label="Genre" type="select" requis register={r} erreur={erreur('genre')}
          options={[{ valeur: 'F', libelle: 'Féminin' }, { valeur: 'M', libelle: 'Masculin' }]} />
        <Champ nom="date_naissance" label="Date de naissance" type="date" register={r} erreur={erreur('date_naissance')} />
        <Champ nom="email" label="E-mail" type="email" register={r} erreur={erreur('email')} />
        <Champ nom="telephone" label="Téléphone" register={r} erreur={erreur('telephone')} />
        {enseignant ? (
          <>
            <Champ nom="departement" label="Département" type="select" requis register={r} erreur={erreur('departement')}
              options={(departements.data ?? []).map((d) => ({ valeur: String(d.id), libelle: `${d.libelle} (${d.faculte_code})` }))} />
            <Champ nom="grade" label="Grade" type="select" register={r} erreur={erreur('grade')}
              options={['Ingénieur', 'Docteur', 'Professeur'].map((g) => ({ valeur: g, libelle: g }))} />
          </>
        ) : (
          <>
            <Champ nom="fonction" label="Fonction" type="select" requis register={r} erreur={erreur('fonction')} options={FONCTIONS} />
            {fonction === 'autre' && <Champ nom="fonction_autre" label="Fonction (précisez)" requis register={r} erreur={erreur('fonction_autre')} />}
            <Champ nom="lieu_travail" label="Lieu de travail" register={r} erreur={erreur('lieu_travail')} />
            <Champ nom="faculte_rattachement" label="Faculté de rattachement" type="select" register={r}
              erreur={erreur('faculte_rattachement')} vide="Aucune"
              options={(facultes.data ?? []).map((f) => ({ valeur: String(f.id), libelle: f.nom }))} />
          </>
        )}
        <h3 className="pt-2 text-sm font-semibold sm:col-span-2">Contrat</h3>
        <ChampsContrat register={r} control={form.control} erreur={erreur} prefixe="contrat_"
          types={enseignant ? TYPES_CONTRAT : TYPES_CONTRAT.filter((t) => t.valeur === 'permanent')} />
        <div className="sm:col-span-2"><ErreurFormulaire message={erreurs.global} /></div>
      </form>
    </FormModal>
  );
}
