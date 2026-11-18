import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import PageHeader from '@/components/shared/PageHeader';
import RessourceCrud from '../components/RessourceCrud';

const SEMESTRES = Array.from({ length: 10 }, (_, i) => ({ valeur: `S${i + 1}`, libelle: `Semestre ${i + 1}` }));

const CONFIG_UES = {
  ressource: 'ues', libelleNouveau: 'Nouvelle UE', libelleLigne: (u) => u.code ?? 'l’UE',
  colonnes: [
    { key: 'code', label: 'Code' },
    { key: 'libelle', label: 'Intitulé' },
    { key: 'semestre', label: 'Semestre' },
    { key: 'rattachement', label: 'Portail / filière' },
    { key: 'credits_total', label: 'Crédits' },
  ],
  champs: [
    { nom: 'code', label: 'Code', requis: true },
    { nom: 'libelle', label: 'Intitulé', requis: true },
    { nom: 'semestre', label: 'Semestre', type: 'select', options: SEMESTRES, requis: true },
    { nom: 'portail', label: 'Portail', aide: 'Pour S1 et S2.',
      source: { ressource: 'portails', libelle: (p) => `${p.code} (${p.faculte_code})` } },
    { nom: 'filiere', label: 'Filière', aide: 'À partir du S3.',
      source: { ressource: 'filieres', libelle: (f) => `${f.code} (${f.faculte_code})` } },
  ],
};

const CONFIG_ECS = {
  ressource: 'ecs', libelleNouveau: 'Nouvel EC', libelleLigne: (e) => e.code ?? 'l’EC',
  colonnes: [
    { key: 'code', label: 'Code' },
    { key: 'libelle', label: 'Intitulé' },
    { key: 'ue_code', label: 'UE' },
    { key: 'credits', label: 'Crédits' },
    { key: 'heures_total', label: 'Heures', render: (e) => `${e.heures_total} h (CM ${e.heures_cm} · TD ${e.heures_td} · TP ${e.heures_tp})` },
    { key: 'departement_libelle', label: 'Département' },
  ],
  champs: [
    { nom: 'code', label: 'Code', requis: true },
    { nom: 'libelle', label: 'Intitulé', requis: true },
    { nom: 'ue', label: 'UE', requis: true, source: { ressource: 'ues', libelle: (u) => `${u.code} — ${u.libelle}` } },
    { nom: 'credits', label: 'Crédits (1 à 6)', type: 'number', requis: true },
    { nom: 'heures_cm', label: 'Heures de CM', type: 'number', defaut: 0 },
    { nom: 'heures_td', label: 'Heures de TD', type: 'number', defaut: 0 },
    { nom: 'heures_tp', label: 'Heures de TP', type: 'number', defaut: 0 },
    { nom: 'departement', label: 'Département porteur', requis: true,
      source: { ressource: 'departements', libelle: (d) => `${d.libelle} (${d.faculte_code})` } },
    { nom: 'description', label: 'Description', type: 'textarea' },
  ],
};

export default function Enseignement() {
  return (
    <div className="space-y-4">
      <PageHeader
        titre="Enseignements"
        description="Unités d’enseignement et éléments constitutifs : on y saisit les notes et on y planifie les séances."
      />
      <Tabs defaultValue="ues">
        <TabsList>
          <TabsTrigger value="ues">Unités d’enseignement</TabsTrigger>
          <TabsTrigger value="ecs">Éléments constitutifs</TabsTrigger>
        </TabsList>
        <TabsContent value="ues" className="pt-4"><RessourceCrud config={CONFIG_UES} enTete={false} /></TabsContent>
        <TabsContent value="ecs" className="pt-4"><RessourceCrud config={CONFIG_ECS} enTete={false} /></TabsContent>
      </Tabs>
    </div>
  );
}
