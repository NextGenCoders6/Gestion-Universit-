import { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import PageHeader from '@/components/shared/PageHeader';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import Champ from '../components/Champ';

export default function Etablissement() {
  const client = useQueryClient();
  const { toast } = useToast();
  const lecture = useQuery({ queryKey: ['parametres', 'etablissement'], queryFn: api.lireEtablissement });
  const form = useForm();
  const [erreurs, setErreurs] = useState({ champs: {}, global: null });
  const { reset } = form;

  useEffect(() => {
    if (lecture.data) reset(lecture.data);
  }, [lecture.data, reset]);

  const enregistrer = useMutation({
    mutationFn: api.modifierEtablissement,
    onSuccess: (data) => {
      client.setQueryData(['parametres', 'etablissement'], data);
      setErreurs({ champs: {}, global: null });
      toast({ title: 'Paramètres enregistrés' });
    },
    onError: (e) => setErreurs(erreursServeur(e, ['nom_secretaire', 'genre_secretaire', 'ville_signature'])),
  });

  return (
    <div className="max-w-xl space-y-4">
      <PageHeader titre="Établissement" description="Signataire et ville utilisés sur les documents officiels." />
      <form
        className="space-y-4 rounded-lg border border-border bg-card p-5"
        onSubmit={form.handleSubmit((v) => enregistrer.mutate({
          nom_secretaire: v.nom_secretaire, genre_secretaire: v.genre_secretaire, ville_signature: v.ville_signature,
        }))}
      >
        <Champ nom="nom_secretaire" label="Secrétaire universitaire" register={form.register} erreur={erreurs.champs.nom_secretaire} />
        <Champ
          nom="genre_secretaire" label="Genre" type="select" register={form.register}
          options={[{ valeur: 'M', libelle: 'Masculin' }, { valeur: 'F', libelle: 'Féminin' }]}
        />
        <Champ nom="ville_signature" label="Ville de signature" requis register={form.register}
          erreur={erreurs.champs.ville_signature ?? form.formState.errors.ville_signature?.message} />
        {lecture.data?.titre_secretaire && (
          <p className="text-sm text-muted-foreground">Titre affiché : {lecture.data.titre_secretaire}</p>
        )}
        <ErreurFormulaire message={erreurs.global} />
        <Button type="submit" disabled={enregistrer.isPending || lecture.isLoading}>Enregistrer</Button>
      </form>
    </div>
  );
}
