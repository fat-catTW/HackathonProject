import type { ServiceIconType } from "../components/ServiceIcon";

const SERVICE_ICON_MAP: Record<string, ServiceIconType> = {
  "冷氣清潔": "aircon",
  "水電維修": "plumbing",
  "家電安裝": "appliance",
  "居家清潔": "cleaning",
  "除蟲": "pest",
  "搬家": "moving",
};

/** 依服務名稱找對應圖示；找不到時 fallback 為 chat 圖示。 */
export function serviceIconType(serviceName: string | null | undefined): ServiceIconType {
  if (!serviceName) return "chat";
  return SERVICE_ICON_MAP[serviceName] ?? "chat";
}
