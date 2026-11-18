import RessourceCrud from '../components/RessourceCrud';

const CONFIG_CLASSES = {
  ressource: 'classes',
  titre: 'Classes',
  description: 'Une classe par niveau et par année : rattachée au portail en L1, à une filière ensuite.',
  libelleNouveau: 'Nouvelle classe',
  libelleLigne: (c) => c.libelle ?? 'la classe',
  colonnes: [
    { key: 'libelle', label: 'Classe' },
    { key: 'parcours_code', label: 'Niveau' },
    { key: 'annee_libelle', label: 'Année' },
  ],
  champs: [
    { nom: 'annee', label: 'Année', requis: true, source: { ressource: 'annees', libelle: (a) => a.libelle } },
    { nom: 'parcours', label: 'Niveau', requis: true, source: { ressource: 'parcours', libelle: (p) => p.code } },
    {
      nom: 'portail', label: 'Portail', aide: 'Pour la L1 uniquement.',
      source: { ressource: 'portails', libelle: (p) => `${p.code} (${p.faculte_code})` },
    },
    {
      nom: 'filiere', label: 'Filière', aide: 'À partir de la L2.',
      source: { ressource: 'filieres', libelle: (f) => `${f.code} (${f.faculte_code})` },
    },
  ],
};

export default function Classes() {
  return <RessourceCrud config={CONFIG_CLASSES} />;
}
