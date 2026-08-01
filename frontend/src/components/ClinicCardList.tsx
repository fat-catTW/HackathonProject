import type { ClinicInfo } from "../types/clinic";
import { ClinicCard } from "./ClinicCard";

interface Props {
  clinics: ClinicInfo[];
  selectedId: string | null;
  recommendedId: string | null;
  recommendReason: string | null;
  onSelect: (id: string) => void;
}

export function ClinicCardList({ clinics, selectedId, recommendedId, recommendReason, onSelect }: Props) {
  return (
    <div className="flex snap-x gap-3 overflow-x-auto pb-2">
      {clinics.map((clinic) => (
        <ClinicCard
          key={clinic.id}
          clinic={clinic}
          selected={selectedId === clinic.id}
          recommended={recommendedId === clinic.id}
          recommendReason={recommendedId === clinic.id ? recommendReason : null}
          onSelect={() => onSelect(clinic.id)}
        />
      ))}
    </div>
  );
}
