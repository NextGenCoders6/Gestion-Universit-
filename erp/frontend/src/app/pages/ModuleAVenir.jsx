import { Inbox } from '@/components/ui/icons';

export default function ModuleAVenir({ module }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
      <Inbox className="size-10 text-muted-foreground" />
      <h3 className="text-lg font-semibold text-foreground">{module.libelle}</h3>
      <p className="max-w-md text-sm text-muted-foreground">Ce module sera disponible dans une prochaine version.</p>
    </div>
  );
}
