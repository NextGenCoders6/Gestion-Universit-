/**
 * Utilisateurs et droits : un niveau par module (comme Odoo), et pour la
 * Scolarité une faculté de rattachement facultative.
 */
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus } from '@/components/ui/icons';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import DataTable from '@/components/shared/DataTable';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import Champ from '@/components/shared/Champ';

const LIBELLES_NIVEAUX = {
  utilisateur: 'Utilisateur', responsable: 'Responsable', secretariat: 'Secrétariat', faculte: 'Faculté',
};

const CHAMPS_UTILISATEUR = ['username', 'password', 'personne_id', 'faculte_rattachee_id', 'is_active', 'groupes'];

function niveauxDepuisGroupes(modules, groupes = []) {
  return Object.fromEntries(modules.map((m) => {
    const niveau = m.niveaux.find((n) => groupes.includes(`${m.code}_${n}`));
    return [`niveau_${m.code}`, niveau ?? ''];
  }));
}

export default function Utilisateurs() {
  const client = useQueryClient();
  const { toast } = useToast();
  const modules = useQuery({ queryKey: ['parametres', 'modules'], queryFn: api.listerModules });
  const utilisateurs = useQuery({ queryKey: ['parametres', 'utilisateurs'], queryFn: () => api.listerUtilisateurs() });
  const facultes = useQuery({ queryKey: ['parametres', 'facultes', {}], queryFn: () => api.lister('facultes') });
  const personnes = useQuery({ queryKey: ['parametres', 'personnes', {}], queryFn: () => api.lister('personnes') });

  const [edition, setEdition] = useState(null);
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const form = useForm();
  const listeModules = modules.data ?? [];
  const niveauScolarite = useWatch({ control: form.control, name: 'niveau_scolarite' });

  const ouvrir = (ligne) => {
    setErreurs({ champs: {}, global: null });
    form.reset({
      username: ligne?.username ?? '',
      password: '',
      personne_id: ligne?.personne_id ? String(ligne.personne_id) : '',
      faculte_rattachee_id: ligne?.faculte_rattachee_id ? String(ligne.faculte_rattachee_id) : '',
      is_active: ligne?.is_active ?? true,
      ...niveauxDepuisGroupes(listeModules, ligne?.groupes),
    });
    setEdition(ligne ?? {});
  };

  const enregistrer = useMutation({
    mutationFn: (v) => {
      const groupes = listeModules
        .filter((m) => v[`niveau_${m.code}`])
        .map((m) => `${m.code}_${v[`niveau_${m.code}`]}`);
      const donnees = {
        username: v.username,
        is_active: Boolean(v.is_active),
        groupes,
        personne_id: v.personne_id ? Number(v.personne_id) : null,
        faculte_rattachee_id: v.niveau_scolarite && v.faculte_rattachee_id ? Number(v.faculte_rattachee_id) : null,
      };
      if (v.password) donnees.password = v.password;
      return edition?.id ? api.modifierUtilisateur(edition.id, donnees) : api.creerUtilisateur(donnees);
    },
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['parametres', 'utilisateurs'] });
      toast({ title: edition?.id ? 'Utilisateur modifié' : 'Utilisateur créé' });
      setEdition(null);
    },
    onError: (error) => setErreurs(erreursServeur(error, CHAMPS_UTILISATEUR)),
  });

  const colonnes = [
    { key: 'username', label: 'Identifiant' },
    { key: 'nom_complet', label: 'Personne' },
    {
      key: 'groupes', label: 'Droits',
      render: (u) => (u.groupes.length === 0
        ? <span className="text-muted-foreground">Aucun</span>
        : (
          <div className="flex flex-wrap gap-1">
            {u.groupes.map((g) => {
              const [code, niveau] = g.split('_');
              const m = listeModules.find((x) => x.code === code);
              return <Badge key={g} variant="secondary">{m?.libelle ?? code} · {LIBELLES_NIVEAUX[niveau] ?? niveau}</Badge>;
            })}
          </div>
        )),
    },
    { key: 'is_active', label: 'Actif', render: (u) => (u.is_active ? 'Oui' : 'Non') },
  ];

  const erreurChamp = (nom) => erreurs.champs[nom] ?? form.formState.errors[nom]?.message;

  return (
    <div className="space-y-4">
      <PageHeader titre="Utilisateurs et droits" description="Un niveau d’accès par module, comme dans Odoo.">
        <Button onClick={() => ouvrir(null)} disabled={modules.isLoading}>
          <Plus className="size-4" /> Nouvel utilisateur
        </Button>
      </PageHeader>

      <DataTable
        columns={colonnes}
        data={utilisateurs.data ?? []}
        isLoading={utilisateurs.isLoading}
        isError={utilisateurs.isError}
        onEdit={ouvrir}
        libelleLigne={(u) => u.username}
        emptyMessage="Aucun utilisateur."
      />

      <FormModal
        open={edition !== null}
        onClose={() => setEdition(null)}
        title={edition?.id ? `Modifier ${edition.username}` : 'Nouvel utilisateur'}
        onConfirm={form.handleSubmit((v) => enregistrer.mutate(v))}
        isPending={enregistrer.isPending}
      >
        <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
          <Champ nom="username" label="Identifiant" requis register={form.register} erreur={erreurChamp('username')} />
          <Champ
            nom="password" label="Mot de passe" type="password" requis={!edition?.id}
            aide={edition?.id ? 'Laisser vide pour ne pas le changer.' : undefined}
            register={form.register} erreur={erreurChamp('password')}
          />
          <Champ
            nom="personne_id" label="Personne liée" type="select" vide="Aucune"
            options={(personnes.data ?? []).map((p) => ({ valeur: String(p.id), libelle: p.nom_complet }))}
            register={form.register} erreur={erreurChamp('personne_id')}
          />
          <Champ nom="is_active" label="Compte actif" type="checkbox" register={form.register} />

          <fieldset className="space-y-3 rounded-lg border border-border p-4">
            <legend className="px-1 text-sm font-semibold text-foreground">Droits par module</legend>
            {listeModules.map((m) => (
              <Champ
                key={m.code}
                nom={`niveau_${m.code}`}
                label={m.libelle}
                type="select"
                vide="Aucun accès"
                options={m.niveaux.map((n) => ({ valeur: n, libelle: LIBELLES_NIVEAUX[n] ?? n }))}
                register={form.register}
              />
            ))}
            {niveauScolarite && (
              <Champ
                nom="faculte_rattachee_id" label="Faculté de rattachement" type="select" vide="Toutes les facultés"
                options={(facultes.data ?? []).map((f) => ({ valeur: String(f.id), libelle: `${f.code} — ${f.nom}` }))}
                register={form.register} erreur={erreurChamp('faculte_rattachee_id')}
              />
            )}
            <ErreurFormulaire message={erreurs.champs.groupes} />
          </fieldset>
          <ErreurFormulaire message={erreurs.global} />
        </form>
      </FormModal>
    </div>
  );
}
