import type { ServiceIconType } from "../components/ServiceIcon";
import { SERVICES } from "../data/services";

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

/**
 * 依 service_id 找圖示。
 *
 * 後端只回 service_id（服務名稱是顯示文案，不該拿來當對照鍵——改個字就對不上了），
 * 圖示對照直接讀服務目錄本身，新增服務時不必再多維護一份 id → icon 的表。
 */
export function serviceIconForId(serviceId: string | null | undefined): ServiceIconType {
  if (!serviceId) return "chat";
  return SERVICES.find((service) => service.service_id === serviceId)?.icon ?? "chat";
}
