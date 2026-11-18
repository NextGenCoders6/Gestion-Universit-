import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Label } from '@/components/ui/label';
import { UserCheck, UserX } from '@/components/ui/icons';
import ErreurFormulaire from '@/components/shared/ErreurFormulaire';
import FormModal from '@/components/shared/FormModal';
import { useToast } from '@/hooks/use-toast';
import { erreursServeur } from '@/lib/erreurs';
import * as api from '../api';
import RessourceCrud from '../components/RessourceCrud';

const ROLES = { etudiant: 'Étudiant', enseignant: 'Enseignant', employe: 'Employé' };

export default function Personnes() {
  const client = useQueryClient();
  const { toast } = useToast();
  const [cible, setCible] = useState(null);
  const [motif, setMotif] = useState('');
  const [erreur, setErreur] = useState(null);

  const rafraichir = () => client.invalidateQueries({ queryKey: ['parametres'] });

  const suspendre = useMutation({
    mutationFn: () => api.agir('personnes', cible.id, 'suspendre', { motif }),
    onSuccess: () => { rafraichir(); toast({ title: 'Personne suspendue' }); setCible(null); },
    onError: (e) => setErreur(erreursServeur(e).champs.motif ?? erreursServeur(e).global),
  });

  const reactiver = useMutation({
    mutationFn: (p) => api.agir('personnes', p.id, 'reactiver'),
    onSuccess: () => { rafraichir(); toast({ title: 'Personne réactivée' }); },
    onError: (e) => toast({ title: 'Échec', description: erreursServeur(e).global, variant: 'destructive' }),
  });

  const config = {
    ressource: 'personnes',
    titre: 'Personnes',
    description: 'Une seule fiche par personne, partagée par tous les modules.',
    libelleNouveau: 'Nouvelle personne',
    libelleLigne: (p) => p.nom_complet ?? 'la personne',
    colonnes: [
      { key: 'nom_complet', label: 'Nom' },
      { key: 'email', label: 'E-mail' },
      { key: 'telephone', label: 'Téléphone' },
      {
        key: 'roles', label: 'Rôles',
        render: (p) => (
          <div className="flex flex-wrap gap-1">
            {(p.roles ?? []).map((r) => <Badge key={r} variant="secondary">{ROLES[r] ?? r}</Badge>)}
          </div>
        ),
      },
      {
        key: 'statut', label: 'Statut',
        render: (p) => (p.statut === 'suspendu'
          ? <span className="font-medium text-destructive" title={p.motif_suspension}>Suspendu</span>
          : 'Actif'),
      },
    ],
    champs: [
      { nom: 'nom', label: 'Nom', requis: true },
      { nom: 'prenom', label: 'Prénom', requis: true },
      { nom: 'genre', label: 'Genre', type: 'select', requis: true,
        options: [{ valeur: 'M', libelle: 'Masculin' }, { valeur: 'F', libelle: 'Féminin' }] },
      { nom: 'date_naissance', label: 'Date de naissance', type: 'date' },
      { nom: 'lieu_naissance', label: 'Lieu de naissance' },
      { nom: 'nationalite', label: 'Nationalité', defaut: 'Congolaise' },
      { nom: 'email', label: 'E-mail', type: 'email' },
      { nom: 'telephone', label: 'Téléphone' },
      { nom: 'adresse', label: 'Adresse' },
    ],
    actions: [
      { libelle: 'Suspendre', icone: UserX, onClick: (p) => { setMotif(''); setErreur(null); setCible(p); } },
      { libelle: 'Réactiver', icone: UserCheck, onClick: (p) => reactiver.mutate(p) },
    ],
  };

  return (
    <>
      <RessourceCrud config={config} />
      <FormModal
        open={cible !== null}
        onClose={() => setCible(null)}
        title={`Suspendre ${cible?.nom_complet ?? ''}`}
        description="La personne ne pourra plus se connecter, même si sa session est ouverte."
        confirmLabel="Suspendre"
        isDestructive
        onConfirm={() => suspendre.mutate()}
        isPending={suspendre.isPending}
      >
        <div className="space-y-1.5">
          <Label htmlFor="motif-suspension">Motif</Label>
          <textarea
            id="motif-suspension"
            rows={3}
            value={motif}
            onChange={(e) => setMotif(e.target.value)}
            className="flex w-full rounded-md border border-border bg-background px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <ErreurFormulaire message={erreur} />
        </div>
      </FormModal>
    </>
  );
}
