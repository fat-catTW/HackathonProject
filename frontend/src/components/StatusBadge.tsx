import type { RequestStatus } from "../types/request";

const STYLES: Record<string, string> = {
  SUBMITTED: "bg-amber-soft text-amber",
  PENDING_PROVIDER: "bg-amber-soft text-amber",
  CONFIRMED: "bg-leaf-soft text-leaf",
  IN_PROGRESS: "bg-leaf-soft text-leaf",
  COMPLETED: "bg-sky-soft text-sky",
  CANCELLED: "bg-gray-100 text-gray-500",
  FAILED: "bg-red-50 text-red-600",
};

export function StatusBadge({
  status,
  label,
}: {
  status: RequestStatus | string;
  label: string;
}) {
  const style = STYLES[status] ?? "bg-gray-100 text-gray-600";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-sm font-medium ${style}`}
    >
      <span className="h-2 w-2 rounded-full bg-current" aria-hidden />
      {label}
    </span>
  );
}
