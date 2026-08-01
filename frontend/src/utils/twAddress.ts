import { counties, getDistrictsByCountyName } from "../data/twRegions";

export interface TwAddressParts {
  county: string;
  district: string;
  detail: string;
}

/** 縣市清單用「台」，使用者與 Agent 可能給「臺」，比對前先統一。 */
function normalize(text: string) {
  return text.replace(/臺/g, "台").trim();
}

/**
 * 把一整串地址拆成「縣市／鄉鎮市區／詳細地址」三段，供 AI 代填 address 欄位使用。
 *
 * 表單的地址欄是三個獨立控制項（兩個下拉 + 一個輸入框），但 Agent 收到與儲存的是
 * 一整串地址，所以代填前要先還原成這三段。拆不出縣市或鄉鎮市區時不猜，整串放進
 * 詳細地址讓使用者自己補選，至少不會把錯的縣市寫進表單。
 */
export function splitTwAddress(address: string): TwAddressParts {
  const raw = (address ?? "").trim();
  if (!raw) return { county: "", district: "", detail: "" };

  const normalized = normalize(raw);
  const county = counties.find((item) => normalized.startsWith(normalize(item.name)));
  if (!county) return { county: "", district: "", detail: raw };

  const rest = normalized.slice(normalize(county.name).length).trim();
  const districts = getDistrictsByCountyName(county.name);
  // 先比長的，避免「東區」先吃掉「東勢區」這種前綴重疊的情況。
  const district = [...districts]
    .sort((left, right) => right.length - left.length)
    .find((item) => rest.startsWith(normalize(item)));
  if (!district) return { county: county.name, district: "", detail: rest };

  return {
    county: county.name,
    district,
    detail: rest.slice(normalize(district).length).trim(),
  };
}
