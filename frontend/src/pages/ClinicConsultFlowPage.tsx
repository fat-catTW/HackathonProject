import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { ClinicCardList } from "../components/ClinicCardList";
import { ClinicSummaryCard } from "../components/ClinicSummaryCard";
import { ServiceIcon } from "../components/ServiceIcon";
import { ShareWithFamilyButton } from "../components/ShareWithFamilyButton";
import { Toast } from "../components/Toast";
import { VoiceButton } from "../components/VoiceButton";
import {
  getCrossSellRecommendations,
  submitClinicAppointment,
  triageSymptom,
} from "../api/clinics";
import { counties, getDistrictsByCountyName } from "../data/twRegions";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import type { ClinicInfo, HealthProductRecommendationItem } from "../types/clinic";

// 「crosssell」與「share」在流程規劃上是兩個不同的關注點（加購推薦 / 分享給家人），
// 但送出掛號成功後，兩者要同時呈現在同一個結果畫面上，不需要使用者再多按一次「下一步」，
// 因此在實作上合併成同一個 "result" 步驟畫面（畫面內容涵蓋 crosssell + share 兩者）。
type Step = "symptom" | "clinic" | "datetime" | "contact" | "summary" | "result";
const STEP_ORDER: Step[] = ["symptom", "clinic", "datetime", "contact", "summary", "result"];

const DEFAULT_CITY = "台中市";
const DEFAULT_DISTRICT = "西屯區";

/** 把第一人稱症狀描述（例如「我一直咳嗽」）轉成適合傳給家人看的簡短敘述（「咳嗽」）。 */
function toShareSymptomPhrase(note: string): string {
  const trimmed = note.trim();
  const stripped = trimmed.replace(/^我(一直|已經|已经|覺得|感覺|好像|最近|有點|有点)*/, "");
  return stripped || trimmed;
}

export function ClinicConsultFlowPage() {
  const navigate = useNavigate();
  const [stepIndex, setStepIndex] = useState(0);
  const [toastText, setToastText] = useState<string | null>(null);

  const [symptomNote, setSymptomNote] = useState("");
  const [city, setCity] = useState(DEFAULT_CITY);
  const [district, setDistrict] = useState(DEFAULT_DISTRICT);
  const [advisory, setAdvisory] = useState("");
  const [clinics, setClinics] = useState<ClinicInfo[]>([]);
  const [recommendedClinicId, setRecommendedClinicId] = useState<string | null>(null);
  const [recommendReason, setRecommendReason] = useState<string | null>(null);
  const [selectedClinicId, setSelectedClinicId] = useState<string | null>(null);
  const [triaging, setTriaging] = useState(false);

  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [contactName, setContactName] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [requestId, setRequestId] = useState<string | null>(null);

  const [crossSellItems, setCrossSellItems] = useState<HealthProductRecommendationItem[]>([]);

  const step = STEP_ORDER[stepIndex];
  const goNext = () => setStepIndex((i) => Math.min(i + 1, STEP_ORDER.length - 1));
  const goBack = () => setStepIndex((i) => Math.max(i - 1, 0));
  const selectedClinic = clinics.find((c) => c.id === selectedClinicId) ?? null;
  const districtOptions = getDistrictsByCountyName(city);

  const speech = useSpeechRecognition((text) => setSymptomNote(text));

  async function submitSymptom() {
    if (!symptomNote.trim() || triaging) return;
    setTriaging(true);
    try {
      const result = await triageSymptom(symptomNote, city, district);
      setAdvisory(result.advisory);
      setClinics(result.clinics);
      setRecommendedClinicId(result.recommended_clinic_id);
      setRecommendReason(result.recommend_reason);
      setSelectedClinicId(result.recommended_clinic_id ?? result.clinics[0]?.id ?? null);
      goNext();
    } catch (error) {
      setToastText(error instanceof Error ? error.message : "查詢失敗，請稍後再試");
    } finally {
      setTriaging(false);
    }
  }

  async function handleConfirmAppointment() {
    if (!selectedClinicId) return;
    setSubmitting(true);
    try {
      const result = await submitClinicAppointment({
        clinic_id: selectedClinicId,
        appointment_date: date,
        appointment_time: time,
        symptom_note: symptomNote,
        contact_name: contactName,
        phone,
      });
      setRequestId(result.request_id);
      const crossSell = await getCrossSellRecommendations(result.request_id);
      setCrossSellItems(crossSell.recommendations);
      goNext();
    } catch (error) {
      setToastText(error instanceof Error ? error.message : "掛號未成功送出，請重新嘗試");
    } finally {
      setSubmitting(false);
    }
  }

  const familyShareText = selectedClinic
    ? `爸爸今天有點${toShareSymptomPhrase(symptomNote)}，已預約${date} ${time}去${selectedClinic.name}看診，請不用擔心。`
    : "";

  return (
    <>
      <main className="mx-auto min-h-dvh max-w-md bg-canvas px-5 pb-32 pt-8">
        <header className="flex items-center gap-3 pb-4">
          <button
            type="button"
            onClick={() => navigate("/home")}
            aria-label="返回"
            className="flex h-11 w-11 items-center justify-center text-[var(--color-muted-foreground)]"
          >
            <ServiceIcon type="back" size={22} />
          </button>
          <h1 className="text-xl font-black text-[var(--color-foreground)]">診所掛號</h1>
        </header>

        {step === "symptom" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">
              請描述您哪裡不舒服
            </p>
            <div className="grid grid-cols-2 gap-3">
              <select
                aria-label="縣市"
                value={city}
                onChange={(e) => {
                  setCity(e.target.value);
                  setDistrict("");
                }}
                className="min-h-[44px] rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5"
              >
                {counties.map((c) => (
                  <option key={c.code} value={c.name}>
                    {c.name}
                  </option>
                ))}
              </select>
              <select
                aria-label="鄉鎮市區"
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="min-h-[44px] rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5"
              >
                <option value="">請選擇</option>
                {districtOptions.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-3">
              <VoiceButton
                listening={speech.listening}
                supported={speech.supported}
                onStart={speech.start}
                onStop={speech.stop}
              />
              <textarea
                aria-label="症狀描述"
                value={symptomNote}
                onChange={(e) => setSymptomNote(e.target.value)}
                placeholder="例如：我今天開始咳嗽，喉嚨癢癢乾乾的"
                rows={4}
                className="min-w-0 flex-1 rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3.5 outline-none focus:border-brand"
              />
            </div>
            <button
              type="button"
              disabled={!symptomNote.trim() || triaging}
              onClick={() => void submitSymptom()}
              className="min-h-[44px] rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
            >
              送出
            </button>
          </section>
        )}

        {step === "clinic" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">{advisory}</p>
            <ClinicCardList
              clinics={clinics}
              selectedId={selectedClinicId}
              recommendedId={recommendedClinicId}
              recommendReason={recommendReason}
              onSelect={setSelectedClinicId}
            />
            <button
              type="button"
              disabled={!selectedClinicId}
              onClick={goNext}
              className="mt-2 min-h-[44px] rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
            >
              下一步
            </button>
          </section>
        )}

        {step === "datetime" && (
          <section className="flex flex-col gap-4">
            <div>
              <label htmlFor="clinic-date" className="block text-base font-bold text-[var(--color-foreground)]">
                看診日期
              </label>
              <input
                id="clinic-date"
                aria-label="看診日期"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 font-[family-name:var(--font-mono)]"
              />
            </div>
            <div>
              <label htmlFor="clinic-time" className="block text-base font-bold text-[var(--color-foreground)]">
                看診時間
              </label>
              <input
                id="clinic-time"
                aria-label="看診時間"
                type="time"
                value={time}
                onChange={(e) => setTime(e.target.value)}
                className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 font-[family-name:var(--font-mono)]"
              />
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button
                type="button"
                disabled={!date || !time}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
              >
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "contact" && (
          <section className="flex flex-col gap-4">
            <div>
              <label htmlFor="clinic-contact-name" className="block text-base font-bold text-[var(--color-foreground)]">
                聯絡人姓名
              </label>
              <input
                id="clinic-contact-name"
                aria-label="聯絡人姓名"
                type="text"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5"
              />
            </div>
            <div>
              <label htmlFor="clinic-contact-phone" className="block text-base font-bold text-[var(--color-foreground)]">
                聯絡電話
              </label>
              <input
                id="clinic-contact-phone"
                aria-label="聯絡電話"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="mt-2 min-h-[44px] w-full rounded-xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-3.5 py-2.5 font-[family-name:var(--font-mono)]"
              />
            </div>
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button
                type="button"
                disabled={!contactName.trim() || !phone.trim()}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
              >
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "summary" && selectedClinic && (
          <ClinicSummaryCard
            data={{
              clinicName: selectedClinic.name,
              clinicAddress: selectedClinic.address,
              date,
              time,
              symptomNote,
              contactName,
              phone,
            }}
            onConfirm={() => void handleConfirmAppointment()}
            onEdit={goBack}
            submitting={submitting}
          />
        )}

        {step === "result" && requestId && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">
              掛號已完成！針對您的狀況，為您推薦以下商品：
            </p>
            {crossSellItems.map((item) => (
              <div
                key={item.product_id}
                className="rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4"
              >
                <p className="text-sm leading-relaxed text-[var(--color-foreground)]">{item.reason}</p>
              </div>
            ))}
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">{familyShareText}</p>
            <ShareWithFamilyButton text={familyShareText} />
            <button
              type="button"
              onClick={() => navigate(`/requests/${requestId}`)}
              className="min-h-[44px] rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
            >
              查看掛號紀錄
            </button>
          </section>
        )}
      </main>

      <Toast text={toastText} onHide={() => setToastText(null)} />
      <ButlerLauncher currentPageId="clinic_appointment_flow" />
    </>
  );
}
