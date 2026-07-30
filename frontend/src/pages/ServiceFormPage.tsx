import { useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { createServiceRequest } from "../api/services";
import { ServiceIcon } from "../components/ServiceIcon";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { Toast } from "../components/Toast";
import { getServiceDefinition } from "../data/services";
import { counties, getDistrictsByCountyName } from "../data/twRegions";
import type { ServiceField } from "../types/service";
import { fieldLabel, fieldValueLabel } from "../utils/fieldLabels";

type FormValues = Record<string, string>;
const ADDRESS_COUNTY_SUFFIX = "__county";
const ADDRESS_DISTRICT_SUFFIX = "__district";
const ADDRESS_DETAIL_SUFFIX = "__detail";

const AIRCON_BASE_PRICE = 2800;
const ANTIBACTERIAL_FILM_PRICE = 500;
const TOP_LOAD_WASHER_PRICE = 2200;
const FRONT_LOAD_WASHER_PRICE = 3800;
const HOME_CLEANING_ESTIMATES: Record<
  string,
  { price: number; unit?: string; note: string }
> = {
  地板清潔: {
    price: 2000,
    note: "一般居家地板清潔多落在基礎到府清潔的起始區間。",
  },
  "石材地板研磨 晶化 拋光": {
    price: 1400,
    unit: "/坪",
    note: "石材地板研磨、晶化與拋光通常依坪數計價，實際金額會看磨耗程度調整。",
  },
  地毯清潔: {
    price: 3000,
    note: "地毯到府清潔常見以單次出工或坪數報價，50 坪以下常見基本價約 3,000 元起。",
  },
  玻璃清潔: {
    price: 2000,
    note: "玻璃清潔常見會有基本出工門檻，窗型與高度不同也會影響報價。",
  },
  天花板除塵: {
    price: 1500,
    note: "天花板除塵多半併入鐘點清潔計價，這裡先以常見基本出工估算。",
  },
  廁所清潔: {
    price: 2000,
    note: "廁所深度清潔常以每間計價，是否需除霉或除水垢會影響最後費用。",
  },
};

function minDateIso() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 10);
}

function isFieldVisible(field: ServiceField, values: FormValues) {
  if (!field.visibleWhen) return true;
  return (values[field.visibleWhen.fieldId] ?? "") === field.visibleWhen.value;
}

function formatPrice(value: number) {
  return new Intl.NumberFormat("zh-TW").format(value);
}

function parseTimeToMinutes(value: string) {
  const [hours, minutes] = value.split(":").map(Number);
  if (!Number.isInteger(hours) || !Number.isInteger(minutes)) return null;
  return hours * 60 + minutes;
}

function formatMinutesAsTime(totalMinutes: number) {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}`;
}

function buildTimeOptions(field: ServiceField) {
  const start = parseTimeToMinutes(field.minValue ?? "00:00");
  const end = parseTimeToMinutes(field.maxValue ?? "23:55");
  const stepMinutes = Math.max(Math.floor((field.step ?? 300) / 60), 1);

  if (start === null || end === null || start > end) return [];

  const options: string[] = [];
  for (let minutes = start; minutes <= end; minutes += stepMinutes) {
    options.push(formatMinutesAsTime(minutes));
  }
  return options;
}

function readFileAsDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error ?? new Error("讀取圖片失敗"));
    reader.readAsDataURL(file);
  });
}

function preventWheelValueChange(event: React.WheelEvent<HTMLInputElement>) {
  if (document.activeElement === event.currentTarget) {
    event.currentTarget.blur();
  }
}

function buildInitialValues(fields: ServiceField[], prefill?: Record<string, string>) {
  const entries: Array<[string, string]> = [];
  for (const field of fields) {
    entries.push([field.id, prefill?.[field.id] ?? ""]);
    if (field.type === "address") {
      entries.push([`${field.id}${ADDRESS_COUNTY_SUFFIX}`, ""]);
      entries.push([`${field.id}${ADDRESS_DISTRICT_SUFFIX}`, ""]);
      entries.push([`${field.id}${ADDRESS_DETAIL_SUFFIX}`, ""]);
    }
  }
  return Object.fromEntries(entries);
}

function numberMin(field: ServiceField) {
  return field.min ?? 1;
}

function numberStep(field: ServiceField) {
  return field.step ?? 1;
}

function sanitizeNumberValue(raw: string, allowDecimal: boolean) {
  let cleaned = allowDecimal ? raw.replace(/[^\d.]/g, "") : raw.replace(/\D/g, "");
  if (allowDecimal) {
    const [head, ...rest] = cleaned.split(".");
    cleaned = rest.length > 0 ? `${head}.${rest.join("")}` : head;
  }
  return cleaned.replace(/^0+(?=\d)/, "");
}

function groupFields(fields: ServiceField[]) {
  const groups = new Map<string, ServiceField[]>();
  for (const field of fields) {
    const title = field.sectionTitle ?? "基本資訊";
    const existing = groups.get(title) ?? [];
    existing.push(field);
    groups.set(title, existing);
  }

  return Array.from(groups.entries()).map(([title, groupFields]) => ({
    title,
    fields: groupFields,
  }));
}

function addressCountyKey(fieldId: string) {
  return `${fieldId}${ADDRESS_COUNTY_SUFFIX}`;
}

function addressDistrictKey(fieldId: string) {
  return `${fieldId}${ADDRESS_DISTRICT_SUFFIX}`;
}

function addressDetailKey(fieldId: string) {
  return `${fieldId}${ADDRESS_DETAIL_SUFFIX}`;
}

function buildStructuredAddress(county: string, district: string, detail: string) {
  const trimmedCounty = county.trim();
  const trimmedDistrict = district.trim();
  const trimmedDetail = detail.trim();
  if (!trimmedCounty || !trimmedDistrict || !trimmedDetail) return "";
  return `${trimmedCounty}${trimmedDistrict}${trimmedDetail}`;
}

export function ServiceFormPage() {
  const { serviceId = "" } = useParams();
  const location = useLocation();
  const navigate = useNavigate();
  const schema = useMemo(() => getServiceDefinition(serviceId), [serviceId]);
  const supportPrefill = (location.state as { supportPrefill?: Record<string, string> } | null)
    ?.supportPrefill;
  const [values, setValues] = useState<FormValues>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [toastText, setToastText] = useState<string | null>(null);
  const [createdRequestId, setCreatedRequestId] = useState<string | null>(null);

  useEffect(() => {
    setValues(buildInitialValues(schema?.fields ?? [], supportPrefill));
    setErrors({});
    setCreatedRequestId(null);
    setToastText(null);
  }, [schema, supportPrefill]);

  useEffect(() => {
    if (!createdRequestId) return;
    const timer = setTimeout(() => navigate(`/requests/${createdRequestId}`), 1200);
    return () => clearTimeout(timer);
  }, [createdRequestId, navigate]);

  const visibleFields = useMemo(
    () => (schema?.fields ?? []).filter((field) => isFieldVisible(field, values)),
    [schema, values],
  );
  const formFields = useMemo(
    () => visibleFields.filter((field) => !field.hidden),
    [visibleFields],
  );
  const groupedFields = useMemo(() => groupFields(formFields), [formFields]);
  const supportContextItems = useMemo(() => {
    if (serviceId !== "customer_support") return [];

    return [
      { label: "目前頁面", value: values.current_page_label },
      { label: "頁面代碼", value: values.current_page_id },
      { label: "關聯案件編號", value: values.related_request_id },
      { label: "關聯服務", value: values.related_service_name },
      { label: "參考 FAQ", value: values.faq_reference },
    ].filter((item) => item.value);
  }, [serviceId, values]);
  const requiredFieldCount = useMemo(
    () => formFields.filter((field) => field.required).length,
    [formFields],
  );
  const completedCount = useMemo(
    () =>
      formFields.filter((field) => {
        const value = (values[field.id] ?? "").trim();
        return field.required && value !== "";
      }).length,
    [formFields, values],
  );
  const airconEstimate = useMemo(() => {
    if (serviceId !== "air_conditioner_cleaning") return null;

    const quantity = Number(values.quantity);
    const quantityValid = Number.isInteger(quantity) && quantity > 0;
    const addonSelected = values.antibacterial_film_addon === "YES";
    const addonQuantity = Number(values.antibacterial_film_quantity);
    const addonQuantityValid = Number.isInteger(addonQuantity) && addonQuantity > 0;

    if (!quantityValid) {
      return {
        ready: false,
        needsAddonQuantity: false,
        baseQuantity: 0,
        addonQuantity: 0,
        baseSubtotal: 0,
        addonSubtotal: 0,
        total: 0,
      };
    }

    const baseSubtotal = quantity * AIRCON_BASE_PRICE;
    const addonSubtotal =
      addonSelected && addonQuantityValid ? addonQuantity * ANTIBACTERIAL_FILM_PRICE : 0;

    return {
      ready: !addonSelected || addonQuantityValid,
      needsAddonQuantity: addonSelected && !addonQuantityValid,
      baseQuantity: quantity,
      addonQuantity: addonSelected && addonQuantityValid ? addonQuantity : 0,
      baseSubtotal,
      addonSubtotal,
      total: baseSubtotal + addonSubtotal,
    };
  }, [serviceId, values]);
  const washerEstimate = useMemo(() => {
    if (serviceId !== "washing_machine_cleaning") return null;

    const quantity = Number(values.quantity);
    const quantityValid = Number.isInteger(quantity) && quantity > 0;
    const machineType = values.machine_type;
    const unitPrice =
      machineType === "TOP_LOAD"
        ? TOP_LOAD_WASHER_PRICE
        : machineType === "FRONT_LOAD"
          ? FRONT_LOAD_WASHER_PRICE
          : 0;

    if (!quantityValid || !unitPrice) {
      return {
        ready: false,
        quantity: quantityValid ? quantity : 0,
        machineType,
        unitPrice,
        total: 0,
      };
    }

    return {
      ready: true,
      quantity,
      machineType,
      unitPrice,
      total: quantity * unitPrice,
    };
  }, [serviceId, values]);
  const homeCleaningEstimate = useMemo(() => {
    if (serviceId !== "home_cleaning") return null;

    const selectedOption = values.cleaning_service_option;
    const estimate = selectedOption ? HOME_CLEANING_ESTIMATES[selectedOption] : null;

    return {
      selectedOption,
      estimate,
    };
  }, [serviceId, values]);

  useEffect(() => {
    if (!schema) return;

    const visibleFieldIds = new Set(visibleFields.map((field) => field.id));

    setValues((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const field of schema.fields) {
        if (!visibleFieldIds.has(field.id) && next[field.id]) {
          next[field.id] = "";
          changed = true;
        }
        if (!visibleFieldIds.has(field.id) && field.type === "address") {
          for (const key of [
            addressCountyKey(field.id),
            addressDistrictKey(field.id),
            addressDetailKey(field.id),
          ]) {
            if (next[key]) {
              next[key] = "";
              changed = true;
            }
          }
        }
      }
      return changed ? next : prev;
    });

    setErrors((prev) => {
      let changed = false;
      const next = { ...prev };
      for (const fieldId of Object.keys(next)) {
        if (!visibleFieldIds.has(fieldId)) {
          delete next[fieldId];
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [schema, visibleFields]);

  function updateValue(fieldOrId: ServiceField | string, value: string) {
    const fieldId = typeof fieldOrId === "string" ? fieldOrId : fieldOrId.id;
    const nextValue =
      typeof fieldOrId === "string" || fieldOrId.type !== "number"
        ? value
        : sanitizeNumberValue(value, !Number.isInteger(numberStep(fieldOrId)));

    setValues((prev) => ({ ...prev, [fieldId]: nextValue }));
    setErrors((prev) => {
      if (!prev[fieldId]) return prev;
      const next = { ...prev };
      delete next[fieldId];
      return next;
    });
  }

  function updateAddressValue(
    fieldId: string,
    nextAddressParts: Partial<Record<"county" | "district" | "detail", string>>,
  ) {
    setValues((prev) => {
      const county = nextAddressParts.county ?? prev[addressCountyKey(fieldId)] ?? "";
      const district = nextAddressParts.district ?? prev[addressDistrictKey(fieldId)] ?? "";
      const detail = nextAddressParts.detail ?? prev[addressDetailKey(fieldId)] ?? "";
      return {
        ...prev,
        [addressCountyKey(fieldId)]: county,
        [addressDistrictKey(fieldId)]: district,
        [addressDetailKey(fieldId)]: detail,
        [fieldId]: buildStructuredAddress(county, district, detail),
      };
    });
    setErrors((prev) => {
      if (!prev[fieldId]) return prev;
      const next = { ...prev };
      delete next[fieldId];
      return next;
    });
  }

  async function handleFileChange(fieldId: string, file: File | null) {
    if (!file) {
      updateValue(fieldId, "");
      return;
    }

    try {
      const dataUrl = await readFileAsDataUrl(file);
      updateValue(fieldId, dataUrl);
    } catch {
      setErrors((prev) => ({ ...prev, [fieldId]: "照片讀取失敗，請重新選擇一張圖片" }));
    }
  }

  function validate() {
    if (!schema) return false;

    const nextErrors: Record<string, string> = {};
    for (const field of formFields) {
      const rawValue = (values[field.id] ?? "").trim();
      if (field.type === "address") {
        const county = (values[addressCountyKey(field.id)] ?? "").trim();
        const district = (values[addressDistrictKey(field.id)] ?? "").trim();
        const detail = (values[addressDetailKey(field.id)] ?? "").trim();
        if (field.required && (!county || !district || !detail)) {
          nextErrors[field.id] = `請完整填寫${field.label}`;
        }
        continue;
      }
      if (field.required && !rawValue) {
        nextErrors[field.id] = `請填寫${field.label}`;
        continue;
      }

      if (field.type === "number" && rawValue) {
        const parsed = Number(rawValue);
        const min = numberMin(field);
        const step = numberStep(field);

        if (!Number.isFinite(parsed) || parsed < min) {
          nextErrors[field.id] = `${field.label}需為 ${min} 以上的數字`;
          continue;
        }
        if (Number.isInteger(step) && !Number.isInteger(parsed)) {
          nextErrors[field.id] = `${field.label}需為整數`;
        }
      }
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function handleSubmit() {
    if (!schema || submitting) return;
    if (!validate()) return;

    const payload: Record<string, string | number> = {};
    for (const field of visibleFields) {
      const rawValue = (values[field.id] ?? "").trim();
      if (!rawValue) continue;
      payload[field.id] = field.type === "number" ? Number(rawValue) : rawValue;
    }

    setSubmitting(true);
    try {
      const result = await createServiceRequest(schema.service_id, payload);
      setCreatedRequestId(result.request_id);
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.code === "INVALID_FORM_DATA" && error.details?.missingFields?.length) {
          setErrors((prev) => {
            const next = { ...prev };
            for (const fieldId of error.details?.missingFields ?? []) {
              next[fieldId] = `請填寫${fieldLabel(fieldId)}`;
            }
            return next;
          });
        }
        setToastText(error.message);
      } else {
        setToastText("送出失敗，請稍後再試");
      }
    } finally {
      setSubmitting(false);
    }
  }

  function renderField(field: ServiceField) {
    const value = values[field.id] ?? "";
    const error = errors[field.id];
    const countyValue = values[addressCountyKey(field.id)] ?? "";
    const districtValue = values[addressDistrictKey(field.id)] ?? "";
    const detailValue = values[addressDetailKey(field.id)] ?? "";
    const districtOptions = field.type === "address" ? getDistrictsByCountyName(countyValue) : [];

    return (
      <label
        key={field.id}
        className="block rounded-[24px] border border-slate-100 bg-slate-50/80 p-4"
      >
        <div className="flex items-start gap-3">
          <span className="mt-0.5 flex h-11 w-11 items-center justify-center rounded-2xl bg-white text-brand shadow-sm">
            <ServiceIcon type={field.inputIcon ?? "info"} size={20} />
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-base font-black text-slate-900">{field.label}</span>
              {field.required && (
                <span className="rounded-full bg-brand-soft px-2 py-0.5 text-[11px] font-bold text-brand">
                  必填
                </span>
              )}
            </div>
            {field.hint && <p className="mt-1 text-sm leading-6 text-slate-500">{field.hint}</p>}

            <div className="mt-3">
              {field.type === "address" ? (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 gap-3">
                    <select
                      aria-label={`${field.label}縣市`}
                      value={countyValue}
                      onChange={(e) =>
                        updateAddressValue(field.id, { county: e.target.value, district: "" })
                      }
                      className="w-full rounded-2xl border-2 border-white bg-white px-4 py-3.5 text-slate-900 outline-none transition focus:border-brand"
                    >
                      <option value="">請選擇縣市</option>
                      {counties.map((county) => (
                        <option key={county.code} value={county.name}>
                          {county.name}
                        </option>
                      ))}
                    </select>
                    <select
                      aria-label={`${field.label}鄉鎮市區`}
                      value={districtValue}
                      disabled={!countyValue}
                      onChange={(e) => updateAddressValue(field.id, { district: e.target.value })}
                      className="w-full rounded-2xl border-2 border-white bg-white px-4 py-3.5 text-slate-900 outline-none transition focus:border-brand disabled:bg-slate-100 disabled:text-slate-400"
                    >
                      <option value="">{countyValue ? "請選擇鄉鎮市區" : "請先選擇縣市"}</option>
                      {districtOptions.map((district) => (
                        <option key={district} value={district}>
                          {district}
                        </option>
                      ))}
                    </select>
                  </div>
                  <input
                    type="text"
                    aria-label={`${field.label}詳細地址`}
                    value={detailValue}
                    onChange={(e) => updateAddressValue(field.id, { detail: e.target.value })}
                    placeholder="例如：大學路一段 168 號 1 樓"
                    className="w-full rounded-2xl border-2 border-white bg-white px-4 py-3.5 text-slate-900 outline-none transition focus:border-brand"
                  />
                </div>
              ) : field.type === "select" ? (
                <select
                  aria-label={field.label}
                  value={value}
                  onChange={(e) => updateValue(field.id, e.target.value)}
                  className="w-full rounded-2xl border-2 border-white bg-white px-4 py-3.5 text-slate-900 outline-none transition focus:border-brand"
                >
                  <option value="">請選擇</option>
                  {(field.options ?? []).map((option) => (
                    <option key={option} value={option}>
                      {fieldValueLabel(option)}
                    </option>
                  ))}
                </select>
              ) : field.type === "time" ? (
                <select
                  aria-label={field.label}
                  value={value}
                  onChange={(e) => updateValue(field.id, e.target.value)}
                  className="w-full rounded-2xl border-2 border-white bg-white px-4 py-3.5 text-slate-900 outline-none transition focus:border-brand"
                >
                  <option value="">請選擇</option>
                  {buildTimeOptions(field).map((option) => (
                    <option key={option} value={option}>
                      {option}
                    </option>
                  ))}
                </select>
              ) : field.type === "file" ? (
                <div className="space-y-3">
                  <input
                    type="file"
                    aria-label={field.label}
                    accept={field.accept}
                    onChange={(e) => void handleFileChange(field.id, e.target.files?.[0] ?? null)}
                    className="block w-full rounded-2xl border-2 border-white bg-white px-4 py-3 text-sm text-slate-600 file:mr-4 file:rounded-full file:border-0 file:bg-brand-soft file:px-4 file:py-2 file:font-bold file:text-brand"
                  />
                  {value && (
                    <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
                      <img src={value} alt={`${field.label}預覽`} className="h-48 w-full object-cover" />
                      <div className="flex items-center justify-between gap-3 px-4 py-3">
                        <p className="text-sm text-slate-500">已選擇現場照片，可送出前再次更換。</p>
                        <button
                          type="button"
                          onClick={() => updateValue(field.id, "")}
                          className="rounded-full border border-slate-200 px-3 py-1 text-sm font-semibold text-slate-500"
                        >
                          移除
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : field.type === "textarea" ? (
                <textarea
                  aria-label={field.label}
                  value={value}
                  onChange={(e) => updateValue(field.id, e.target.value)}
                  rows={field.rows ?? 4}
                  placeholder={field.placeholder ?? `請填寫${field.label}`}
                  className="w-full rounded-2xl border-2 border-white bg-white px-4 py-3.5 text-slate-900 outline-none transition focus:border-brand"
                />
              ) : (
                <input
                  type={
                    field.type === "number"
                      ? "number"
                      : field.type === "date"
                        ? "date"
                      : "text"
                  }
                  aria-label={field.label}
                  inputMode={field.type === "number" ? "numeric" : undefined}
                  min={
                    field.type === "date"
                      ? minDateIso()
                      : field.type === "number"
                        ? numberMin(field)
                        : undefined
                  }
                  step={field.type === "number" ? numberStep(field) : undefined}
                  value={value}
                  onChange={(e) => updateValue(field, e.target.value)}
                  onWheel={field.type === "number" ? preventWheelValueChange : undefined}
                  onKeyDown={
                    field.type === "number"
                      ? (event) => {
                          if (["-", "+", "e", "E"].includes(event.key)) event.preventDefault();
                        }
                      : undefined
                  }
                  placeholder={
                    field.type === "text" || field.type === "number"
                      ? field.placeholder ?? `請填寫${field.label}`
                      : undefined
                  }
                  className="w-full rounded-2xl border-2 border-white bg-white px-4 py-3.5 text-slate-900 outline-none transition focus:border-brand"
                />
              )}
            </div>

            {error && <p className="mt-2 text-sm font-medium text-red-600">{error}</p>}
          </div>
        </div>
      </label>
    );
  }

  if (!schema) {
    return (
      <>
        <main className="mx-auto min-h-dvh max-w-md bg-canvas px-5 pb-32 pt-16 text-center">
          <p className="text-red-600">找不到這個服務表單。</p>
          <button
            type="button"
            onClick={() => navigate("/home")}
            className="mt-4 text-brand underline"
          >
            返回服務首頁
          </button>
        </main>
        <ButlerLauncher currentPageId="service_form" />
      </>
    );
  }

  return (
    <>
      <main className="mx-auto min-h-dvh max-w-md bg-[linear-gradient(180deg,var(--color-brand-soft)_0%,var(--color-canvas)_100%)] px-5 pb-32 pt-6">
        <header className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate("/home")}
            className="flex h-11 w-11 items-center justify-center rounded-full bg-white text-gray-500 shadow-sm transition hover:text-brand"
          >
            <ServiceIcon type="back" size={20} />
          </button>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-brand">服務表單</p>
            <h1 className="truncate text-2xl font-black text-slate-900">{schema.title}</h1>
          </div>
        </header>

        <section className="mt-6 overflow-hidden rounded-[30px] bg-gradient-to-br from-brand to-brand-dark p-6 text-white shadow-[0_24px_60px_rgba(15,76,129,0.22)]">
          <div className="flex items-start gap-4">
            <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/12">
              <ServiceIcon type={schema.icon} size={30} />
            </span>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold tracking-wide text-white/75">到府服務需求</p>
              <h2 className="mt-1 text-2xl font-black">{schema.title}</h2>
              <p className="mt-3 text-sm leading-7 text-white/80">{schema.description}</p>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-3 gap-3">
            <div className="rounded-2xl bg-white/10 px-3 py-3">
              <p className="text-[11px] font-semibold text-white/70">步驟 1</p>
              <p className="mt-1 text-sm font-bold">填寫需求</p>
            </div>
            <div className="rounded-2xl bg-white/10 px-3 py-3">
              <p className="text-[11px] font-semibold text-white/70">步驟 2</p>
              <p className="mt-1 text-sm font-bold">送出表單</p>
            </div>
            <div className="rounded-2xl bg-white/10 px-3 py-3">
              <p className="text-[11px] font-semibold text-white/70">步驟 3</p>
              <p className="mt-1 text-sm font-bold">等待確認</p>
            </div>
          </div>
        </section>

        <section className="mt-6 rounded-[28px] bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-sm font-semibold text-brand">填寫進度</p>
              <h2 className="mt-1 text-lg font-black text-slate-900">
                已完成 {completedCount} / {requiredFieldCount} 項
              </h2>
            </div>
            <span className="rounded-full bg-brand-soft px-3 py-1 text-xs font-bold text-brand">
              本地表單
            </span>
          </div>
          <div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-brand transition-all"
              style={{ width: `${(completedCount / Math.max(requiredFieldCount, 1)) * 100}%` }}
            />
          </div>
        </section>

        {supportContextItems.length > 0 && (
          <section className="mt-6 rounded-[28px] border border-brand/10 bg-white p-5 shadow-sm">
            <div className="mb-4">
              <p className="text-sm font-semibold text-brand">已自動帶入</p>
              <h3 className="mt-1 text-lg font-black text-slate-900">客服可直接看到這些上下文</h3>
            </div>
            <div className="space-y-3">
              {supportContextItems.map((item) => (
                <div
                  key={item.label}
                  className="flex items-start justify-between gap-4 rounded-2xl bg-slate-50 px-4 py-3"
                >
                  <span className="text-sm text-slate-500">{item.label}</span>
                  <span className="text-right text-sm font-bold text-slate-900">{item.value}</span>
                </div>
              ))}
            </div>
          </section>
        )}

        <section className="mt-6 space-y-5">
          {groupedFields.map((group) => (
            <div key={group.title} className="rounded-[28px] bg-white p-5 shadow-sm">
              <div className="mb-4">
                <p className="text-sm font-semibold text-brand">{group.title}</p>
                <h3 className="mt-1 text-lg font-black text-slate-900">請完成這一區資料</h3>
              </div>
              <div className="space-y-4">{group.fields.map(renderField)}</div>
            </div>
          ))}
        </section>

        {airconEstimate && (
          <section className="mt-6 rounded-[28px] bg-white p-5 shadow-sm">
            <div className="mb-4">
              <p className="text-sm font-semibold text-brand">目前估價</p>
              <h3 className="mt-1 text-lg font-black text-slate-900">依照目前選項試算最低費用</h3>
            </div>

            {!airconEstimate.ready && airconEstimate.baseQuantity === 0 ? (
              <p className="text-sm leading-7 text-slate-500">
                請先填寫有效的冷氣數量，系統就會顯示目前服務的最低估價。
              </p>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
                  <span className="text-sm text-slate-500">
                    冷氣清潔 {airconEstimate.baseQuantity} 台 x {formatPrice(AIRCON_BASE_PRICE)} 元
                  </span>
                  <span className="font-bold text-slate-900">
                    {formatPrice(airconEstimate.baseSubtotal)} 元起
                  </span>
                </div>

                {values.antibacterial_film_addon === "YES" && (
                  <div className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
                    <span className="text-sm text-slate-500">
                      日本抗菌膜{" "}
                      {airconEstimate.addonQuantity > 0
                        ? `${airconEstimate.addonQuantity} 個 x ${formatPrice(ANTIBACTERIAL_FILM_PRICE)} 元`
                        : "尚未填寫數量"}
                    </span>
                    <span className="font-bold text-slate-900">
                      {airconEstimate.addonQuantity > 0
                        ? `${formatPrice(airconEstimate.addonSubtotal)} 元`
                        : "待補數量"}
                    </span>
                  </div>
                )}

                {airconEstimate.needsAddonQuantity ? (
                  <p className="text-sm leading-7 text-amber-600">
                    已選擇加購日本抗菌膜，請填寫有效數量後才會完成完整估價。
                  </p>
                ) : (
                  <div className="rounded-[24px] bg-brand-soft px-4 py-4">
                    <p className="text-sm font-semibold text-brand">最低估價</p>
                    <p className="mt-1 text-2xl font-black text-slate-900">
                      {formatPrice(airconEstimate.total)} 元起
                    </p>
                    <p className="mt-2 text-sm leading-6 text-slate-500">
                      例如：冷氣清潔 2 台 + 日本抗菌膜 2 個 = 6,600 元起
                    </p>
                  </div>
                )}
              </div>
            )}
          </section>
        )}

        {washerEstimate && (
          <section className="mt-6 rounded-[28px] bg-white p-5 shadow-sm">
            <div className="mb-4">
              <p className="text-sm font-semibold text-brand">目前估價</p>
              <h3 className="mt-1 text-lg font-black text-slate-900">依照目前選項試算最低費用</h3>
            </div>

            {!washerEstimate.quantity ? (
              <p className="text-sm leading-7 text-slate-500">
                請先填寫有效的洗衣機數量，系統就會顯示目前服務的最低估價。
              </p>
            ) : !washerEstimate.ready ? (
              <p className="text-sm leading-7 text-slate-500">
                請先選擇洗衣機類型，系統就會顯示目前服務的最低估價。
              </p>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
                  <span className="text-sm text-slate-500">
                    {fieldValueLabel(washerEstimate.machineType)}洗衣機 {washerEstimate.quantity} 台 x{" "}
                    {formatPrice(washerEstimate.unitPrice)} 元
                  </span>
                  <span className="font-bold text-slate-900">
                    {formatPrice(washerEstimate.total)} 元起
                  </span>
                </div>

                <div className="rounded-[24px] bg-brand-soft px-4 py-4">
                  <p className="text-sm font-semibold text-brand">最低估價</p>
                  <p className="mt-1 text-2xl font-black text-slate-900">
                    {formatPrice(washerEstimate.total)} 元起
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    直立式洗衣機 1 台 2,200 元起，滾筒式洗衣機 1 台 3,800 元起。
                  </p>
                </div>
              </div>
            )}
          </section>
        )}

        {homeCleaningEstimate && (
          <section className="mt-6 rounded-[28px] bg-white p-5 shadow-sm">
            <div className="mb-4">
              <p className="text-sm font-semibold text-brand">目前估價</p>
              <h3 className="mt-1 text-lg font-black text-slate-900">依照目前選項試算最低費用</h3>
            </div>

            {!homeCleaningEstimate.selectedOption || !homeCleaningEstimate.estimate ? (
              <p className="text-sm leading-7 text-slate-500">
                請先選擇服務選項，系統就會顯示目前服務的常見估價。
              </p>
            ) : (
              <div className="space-y-3">
                <div className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-4 py-3">
                  <span className="text-sm text-slate-500">
                    {homeCleaningEstimate.selectedOption}
                  </span>
                  <span className="font-bold text-slate-900">
                    {formatPrice(homeCleaningEstimate.estimate.price)} 元
                    {homeCleaningEstimate.estimate.unit ?? ""}起
                  </span>
                </div>

                <div className="rounded-[24px] bg-brand-soft px-4 py-4">
                  <p className="text-sm font-semibold text-brand">最低估價</p>
                  <p className="mt-1 text-2xl font-black text-slate-900">
                    {formatPrice(homeCleaningEstimate.estimate.price)} 元
                    {homeCleaningEstimate.estimate.unit ?? ""}起
                  </p>
                  <p className="mt-2 text-sm leading-6 text-slate-500">
                    {homeCleaningEstimate.estimate.note}
                  </p>
                </div>
              </div>
            )}
          </section>
        )}

        <section className="mt-6 rounded-[28px] border border-white/80 bg-white/96 p-4 shadow-[0_24px_60px_rgba(30,41,59,0.14)]">
          <div className="mb-3">
            <p className="text-sm font-semibold text-brand">送出前提醒</p>
            <p className="mt-1 text-sm text-slate-500">
              缺漏欄位會在送出時提示，你也可以改用 AI 管家協助整理需求。
            </p>
          </div>
          <div className="flex flex-col gap-3">
            <button
              type="button"
              onClick={() => void handleSubmit()}
              disabled={submitting}
              className="w-full rounded-2xl bg-brand py-4 text-base font-bold text-white shadow-[0_16px_34px_rgba(15,76,129,0.22)] disabled:opacity-50"
            >
              {submitting ? "送出中..." : "送出服務需求"}
            </button>
            <button
              type="button"
              onClick={() => navigate("/home")}
              className="w-full rounded-2xl border-2 border-gray-200 bg-white py-4 text-base font-bold text-gray-500"
            >
              返回服務首頁
            </button>
          </div>
        </section>
      </main>

      {createdRequestId && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-[rgba(8,15,30,0.55)] px-6 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-[32px] bg-white p-8 text-center shadow-[0_28px_80px_rgba(15,23,42,0.28)]">
            <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-brand shadow-[0_0_0_12px_rgba(234,241,252,0.9)]">
              <ServiceIcon type="check" size={34} className="text-white" />
            </div>
            <p className="mt-6 text-sm font-semibold uppercase tracking-[0.24em] text-brand">
              Success
            </p>
            <h2 className="mt-2 text-2xl font-black text-slate-900">需求已成功送出</h2>
            <p className="mt-3 text-sm leading-7 text-slate-500">
              我們正在為你建立案件，接下來會自動帶你前往服務詳情頁查看進度。
            </p>
          </div>
        </div>
      )}

      <Toast text={toastText} onHide={() => setToastText(null)} />
      {schema.service_id !== "customer_support" && <ButlerLauncher currentPageId="service_form" />}
    </>
  );
}
