import { Link } from "react-router-dom";
import type { RequestListItem } from "../types/request";
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
      className="block rounded-2xl border border-pine-soft bg-white p-4 shadow-sm transition hover:border-pine focus-visible:outline focus-visible:outline-2 focus-visible:outline-pine"
    >
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-lg font-bold">{item.service_name}</p>
          <p className="mt-0.5 text-sm text-gray-500">{time}</p>
        </div>
        <StatusBadge status={item.status} label={item.status_label} />
      </div>
    </Link>
  );
}
