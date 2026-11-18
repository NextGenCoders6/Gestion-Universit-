/**
 * Écran générique liste + création / modification / suppression d'une
 * ressource du référentiel, décrit par une configuration :
 *
 * {
 *   ressource: 'facultes',                       // /api/core/facultes/
 *   titre, description, libelleNouveau,
 *   colonnes: [{ key, label, render? }],         // pour DataTable
 *   champs: [{ nom, label, type, requis?, options?, source?, defaut? }],
 *     // source : { ressource, libelle: (o) => string } → <select> rempli depuis l'API,
 *     //          valeur envoyée = id numérique ou null
 *   libelleLigne: (ligne) => string,
 *   actions?: [{ libelle, icone, onClick(ligne) }],
 *   lectureSeule?: bool,
 * }
 */
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus } from '@/components/ui/icons';
import { Button } from '@/components/ui/button';
import DataTable from '@/components/shared/DataTable';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import Champ from './Champ';
import { valeursInitiales, versApi } from './formulaire';

function useListe(ressource, params) {
  return useQuery({ queryKey: ['parametres', ressource, params ?? {}], queryFn: () => api.lister(ressource, params) });
}

export default function RessourceCrud({ config, params, enTete = true }) {
  const { ressource, champs, colonnes } = config;
  const client = useQueryClient();
  const { toast } = useToast();
  const liste = useListe(ressource, params);
  const sources = champs.filter((c) => c.source);
  const options = useQueries({
    queries: sources.map((c) => ({
      queryKey: ['parametres', c.source.ressource, {}],
      queryFn: () => api.lister(c.source.ressource),
    })),
  });

  const [edition, setEdition] = useState(null); // null = fermé, {} = création, ligne = modification
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const form = useForm();

  const ouvrir = (ligne) => {
    setErreurs({ champs: {}, global: null });
    form.reset(valeursInitiales(champs, ligne));
    setEdition(ligne ?? {});
  };

  const enregistrer = useMutation({
    mutationFn: (valeurs) => (edition?.id
      ? api.modifier(ressource, edition.id, versApi(champs, valeurs))
      : api.creer(ressource, versApi(champs, valeurs))),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['parametres'] });
      toast({ title: edition?.id ? 'Modifications enregistrées' : 'Élément créé' });
      setEdition(null);
    },
    onError: (error) => setErreurs(erreursServeur(error, champs.map((c) => c.nom))),
  });

  const supprimer = useMutation({
    mutationFn: (ligne) => api.supprimer(ressource, ligne.id),
    onSuccess: () => {
      client.invalidateQueries({ queryKey: ['parametres'] });
      toast({ title: 'Élément supprimé' });
    },
    onError: (error) => toast({ title: 'Suppression impossible', description: erreursServeur(error).global, variant: 'destructive' }),
  });

  const erreurChamp = (nom) => erreurs.champs[nom] ?? form.formState.errors[nom]?.message;

  return (
    <div className="space-y-4">
      {enTete ? (
        <PageHeader titre={config.titre} description={config.description}>
          {!config.lectureSeule && (
            <Button onClick={() => ouvrir(null)}><Plus className="size-4" /> {config.libelleNouveau}</Button>
          )}
        </PageHeader>
      ) : (
        !config.lectureSeule && (
          <div className="flex justify-end">
            <Button onClick={() => ouvrir(null)}><Plus className="size-4" /> {config.libelleNouveau}</Button>
          </div>
        )
      )}

      <DataTable
        columns={colonnes}
        data={liste.data ?? []}
        isLoading={liste.isLoading}
        isError={liste.isError}
        onEdit={config.lectureSeule ? undefined : ouvrir}
        onDelete={config.lectureSeule ? undefined : (ligne) => supprimer.mutate(ligne)}
        actionsSupplementaires={config.actions ?? []}
        actionsEnMenu={Boolean(config.actions?.length)}
        libelleLigne={config.libelleLigne}
        emptyMessage="Aucun élément pour l’instant."
      />

      <FormModal
        open={edition !== null}
        onClose={() => setEdition(null)}
        title={edition?.id ? `Modifier ${config.libelleLigne(edition)}` : config.libelleNouveau}
        onConfirm={form.handleSubmit((valeurs) => enregistrer.mutate(valeurs))}
        isPending={enregistrer.isPending}
      >
        <form className="space-y-4" onSubmit={(e) => e.preventDefault()}>
          {champs.map((c) => {
            const i = sources.indexOf(c);
            const opts = c.source
              ? (options[i]?.data ?? []).map((o) => ({ valeur: String(o.id), libelle: c.source.libelle(o) }))
              : c.options;
            return (
              <Champ
                key={c.nom}
                {...c}
                type={c.source ? 'select' : c.type}
                options={opts}
                register={form.register}
                erreur={erreurChamp(c.nom)}
              />
            );
          })}
          <ErreurFormulaire message={erreurs.global} />
        </form>
      </FormModal>
    </div>
  );
}
