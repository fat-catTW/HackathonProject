import type { RequestStatus } from "../types/request";

const COMPLETED_STYLE = "bg-info-soft text-info";

const STYLES: Record<string, string> = {
  SUBMITTED: "bg-accent-soft text-accent",
  PENDING_PROVIDER: "bg-accent-soft text-accent",
  CONFIRMED: "bg-success-soft text-success",
  IN_PROGRESS: "bg-success-soft text-success",
  COMPLETED: COMPLETED_STYLE,
  CANCELLED: "bg-gray-100 text-gray-500",
  FAILED: "bg-red-50 text-danger",
  VERIFIED: COMPLETED_STYLE,
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
