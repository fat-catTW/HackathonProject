import { Link } from "react-router-dom";
import type { RequestListItem } from "../types/request";
import { ServiceIcon } from "./ServiceIcon";
import { serviceIconType } from "../utils/serviceIcons";
import { StatusBadge } from "./StatusBadge";

export function RequestCard({ item }: { item: RequestListItem }) {
  const time = new Date(item.updated_at).toLocaleString("zh-TW", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  return (
    <Link
      to={`/requests/${item.request_id}`}
      className="flex items-center gap-4 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm transition hover:border-brand focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand"
    >
      <span className="flex h-13 w-13 shrink-0 items-center justify-center rounded-2xl bg-brand-soft text-brand">
        <ServiceIcon type={serviceIconType(item.service_name)} size={26} />
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-lg font-bold">{item.service_name}</p>
        <p className="mt-0.5 text-sm text-gray-500">{time}</p>
      </div>
      <StatusBadge status={item.status} label={item.status_label} />
    </Link>
  );
}
