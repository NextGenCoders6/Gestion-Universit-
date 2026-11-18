import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import PageHeader from '@/components/shared/PageHeader';
import RessourceCrud from '../components/RessourceCrud';

const GENRES = [{ valeur: 'M', libelle: 'Masculin' }, { valeur: 'F', libelle: 'Féminin' }];

const ONGLETS_REFERENTIEL = [
  {
    code: 'annees', titre: 'Années',
    config: {
      ressource: 'annees', libelleNouveau: 'Nouvelle année', libelleLigne: (a) => a.libelle ?? 'l’année',
      colonnes: [
        { key: 'libelle', label: 'Année' },
        { key: 'date_debut', label: 'Début' },
        { key: 'date_fin', label: 'Fin' },
        { key: 'statut', label: 'Statut', render: (a) => (a.statut === 'archivee' ? 'Archivée' : 'Active') },
        { key: 'en_cours', label: 'En cours', render: (a) => (a.en_cours ? 'Oui' : '') },
      ],
      champs: [
        { nom: 'libelle', label: 'Libellé (AAAA-AAAA)', requis: true },
        { nom: 'date_debut', label: 'Date de début', type: 'date', requis: true },
        { nom: 'date_fin', label: 'Date de fin', type: 'date', requis: true },
        { nom: 'statut', label: 'Statut', type: 'select', defaut: 'active',
          options: [{ valeur: 'active', libelle: 'Active' }, { valeur: 'archivee', libelle: 'Archivée' }] },
        { nom: 'en_cours', label: 'Année en cours', type: 'checkbox' },
      ],
    },
  },
  {
    code: 'periodes', titre: 'Périodes',
    config: {
      ressource: 'periodes', libelleNouveau: 'Nouvelle période', libelleLigne: () => 'la période',
      colonnes: [
        { key: 'numero', label: 'Semestre', render: (p) => `Semestre ${p.numero}` },
        { key: 'date_debut', label: 'Début' },
        { key: 'date_fin', label: 'Fin' },
      ],
      champs: [
        { nom: 'annee', label: 'Année', requis: true, source: { ressource: 'annees', libelle: (a) => a.libelle } },
        { nom: 'numero', label: 'Semestre', type: 'number', requis: true,
          aide: '1 = semestres impairs (S1, S3…), 2 = semestres pairs.' },
        { nom: 'date_debut', label: 'Date de début', type: 'date', requis: true },
        { nom: 'date_fin', label: 'Date de fin', type: 'date', requis: true },
      ],
    },
  },
  {
    code: 'facultes', titre: 'Facultés',
    config: {
      ressource: 'facultes', libelleNouveau: 'Nouvelle faculté', libelleLigne: (f) => f.nom ?? 'la faculté',
      colonnes: [
        { key: 'code', label: 'Code' },
        { key: 'nom', label: 'Nom' },
        { key: 'nom_doyen', label: 'Doyen(ne)' },
      ],
      champs: [
        { nom: 'code', label: 'Code', requis: true },
        { nom: 'nom', label: 'Nom', requis: true },
        { nom: 'nom_doyen', label: 'Nom du doyen ou de la doyenne' },
        { nom: 'genre_doyen', label: 'Genre (doyen)', type: 'select', options: GENRES, defaut: 'M' },
        { nom: 'nom_vice_doyen', label: 'Nom du vice-doyen ou de la vice-doyenne' },
        { nom: 'genre_vice_doyen', label: 'Genre (vice-doyen)', type: 'select', options: GENRES, defaut: 'M' },
      ],
    },
  },
  {
    code: 'departements', titre: 'Départements',
    config: {
      ressource: 'departements', libelleNouveau: 'Nouveau département', libelleLigne: (d) => d.libelle ?? 'le département',
      colonnes: [
        { key: 'libelle', label: 'Département' },
        { key: 'faculte_code', label: 'Faculté' },
        { key: 'chef_nom', label: 'Chef de département' },
      ],
      champs: [
        { nom: 'libelle', label: 'Libellé', requis: true },
        { nom: 'faculte', label: 'Faculté', requis: true, source: { ressource: 'facultes', libelle: (f) => f.code } },
      ],
    },
  },
  {
    code: 'portails', titre: 'Portails',
    config: {
      ressource: 'portails', libelleNouveau: 'Nouveau portail', libelleLigne: (p) => p.code ?? 'le portail',
      colonnes: [
        { key: 'code', label: 'Code' },
        { key: 'nom', label: 'Nom' },
        { key: 'faculte_code', label: 'Faculté' },
      ],
      champs: [
        { nom: 'code', label: 'Code', requis: true },
        { nom: 'nom', label: 'Nom', requis: true },
        { nom: 'faculte', label: 'Faculté', requis: true, source: { ressource: 'facultes', libelle: (f) => f.code } },
      ],
    },
  },
  {
    code: 'filieres', titre: 'Filières',
    config: {
      ressource: 'filieres', libelleNouveau: 'Nouvelle filière', libelleLigne: (f) => f.nom ?? 'la filière',
      colonnes: [
        { key: 'code', label: 'Code' },
        { key: 'nom', label: 'Nom' },
        { key: 'departement_libelle', label: 'Département' },
        { key: 'portail_code', label: 'Portail d’origine' },
      ],
      champs: [
        { nom: 'code', label: 'Code', requis: true },
        { nom: 'nom', label: 'Nom', requis: true },
        { nom: 'departement', label: 'Département', requis: true,
          source: { ressource: 'departements', libelle: (d) => `${d.libelle} (${d.faculte_code})` } },
        { nom: 'portail', label: 'Portail d’origine', requis: true,
          source: { ressource: 'portails', libelle: (p) => `${p.code} (${p.faculte_code})` } },
      ],
    },
  },
  {
    code: 'parcours', titre: 'Niveaux',
    config: {
      ressource: 'parcours', libelleNouveau: 'Nouveau niveau', libelleLigne: (p) => p.code ?? 'le niveau',
      colonnes: [
        { key: 'code', label: 'Code' },
        { key: 'type_parcours', label: 'Type' },
        { key: 'semestres', label: 'Semestres', render: (p) => (p.semestres ?? []).join(' + ') },
      ],
      champs: [
        { nom: 'type_parcours', label: 'Type', type: 'select', requis: true,
          options: ['Licence', 'Master', 'Doctorat'].map((t) => ({ valeur: t, libelle: t })) },
        { nom: 'niveau', label: 'Niveau', type: 'number', requis: true },
      ],
    },
  },
];

export default function Referentiel() {
  return (
    <div className="space-y-4">
      <PageHeader titre="Référentiel académique" description="Calendrier et organisation partagés par tous les modules." />
      <Tabs defaultValue="annees">
        <TabsList className="flex-wrap">
          {ONGLETS_REFERENTIEL.map((o) => <TabsTrigger key={o.code} value={o.code}>{o.titre}</TabsTrigger>)}
        </TabsList>
        {ONGLETS_REFERENTIEL.map((o) => (
          <TabsContent key={o.code} value={o.code} className="pt-4">
            <RessourceCrud config={o.config} enTete={false} />
          </TabsContent>
        ))}
      </Tabs>
    </div>
  );
}
