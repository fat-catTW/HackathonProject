import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { PeopleCounter } from "../components/PeopleCounter";
import { PremiumToggle } from "../components/PremiumToggle";
import { ReservationContactForm } from "../components/ReservationContactForm";
import { ReservationDatePicker } from "../components/ReservationDatePicker";
import { ReservationSummaryCard } from "../components/ReservationSummaryCard";
import { RestaurantCardList } from "../components/RestaurantCardList";
import { ServiceIcon } from "../components/ServiceIcon";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { TimeSlotSelector } from "../components/TimeSlotSelector";
import { Toast } from "../components/Toast";
import { listRestaurants, submitReservation } from "../api/reservations";
import type { RestaurantInfo, TimeSlot } from "../types/reservation";

type Step = "restaurant" | "date" | "time" | "people" | "contact" | "premium" | "summary";
const STEP_ORDER: Step[] = ["restaurant", "date", "time", "people", "contact", "premium", "summary"];

export function ReservationFlowPage() {
  const navigate = useNavigate();
  const [restaurants, setRestaurants] = useState<RestaurantInfo[]>([]);
  const [stepIndex, setStepIndex] = useState(0);
  const [restaurantId, setRestaurantId] = useState<string | null>(null);
  const [date, setDate] = useState("");
  const [timeSlot, setTimeSlot] = useState<TimeSlot | null>(null);
  const [specificTime, setSpecificTime] = useState<string | null>(null);
  const [people, setPeople] = useState(2);
  const [contactName, setContactName] = useState("");
  const [phone, setPhone] = useState("");
  const [isPremium, setIsPremium] = useState<boolean | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [toastText, setToastText] = useState<string | null>(null);

  useEffect(() => {
    listRestaurants()
      .then(setRestaurants)
      .catch(() => setToastText("目前無法載入餐廳清單，您可以留下需求由客服為您安排。"));
  }, []);

  const step = STEP_ORDER[stepIndex];
  const goNext = () => setStepIndex((i) => Math.min(i + 1, STEP_ORDER.length - 1));
  const goBack = () => setStepIndex((i) => Math.max(i - 1, 0));

  const selectedRestaurant = restaurants.find((r) => r.id === restaurantId) ?? null;

  async function handleConfirm() {
    if (!restaurantId || !timeSlot || isPremium === null) return;
    setSubmitting(true);
    try {
      const result = await submitReservation({
        restaurant_id: restaurantId,
        reserved_date: date,
        time_slot: timeSlot,
        specific_time: specificTime,
        people,
        contact_name: contactName,
        phone,
        is_premium: isPremium,
      });
      navigate(`/requests/${result.request_id}`);
    } catch (err) {
      setSubmitting(false);
      setToastText(err instanceof Error ? err.message : "訂位未成功送出，請重新嘗試");
    }
  }

  return (
    <>
      <main className="mx-auto min-h-dvh max-w-md bg-canvas px-5 pb-32 pt-8">
        <header className="flex items-center gap-3 pb-4">
          <button type="button" onClick={() => navigate("/home")} aria-label="返回" className="flex h-11 w-11 items-center justify-center text-[var(--color-muted-foreground)]">
            <ServiceIcon type="back" size={22} />
          </button>
          <h1 className="text-xl font-black text-[var(--color-foreground)]">餐廳訂位</h1>
        </header>

        {step === "restaurant" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">請選擇想去的餐廳</p>
            <RestaurantCardList
              restaurants={restaurants}
              selectedId={restaurantId}
              onSelect={setRestaurantId}
              onNeedHelp={() => setToastText("已為您記錄需求，客服將協助媒合餐廳。")}
            />
            <button
              type="button"
              disabled={!restaurantId}
              onClick={goNext}
              className="mt-2 min-h-[44px] rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
            >
              下一步
            </button>
          </section>
        )}

        {step === "date" && (
          <section className="flex flex-col gap-4">
            <ReservationDatePicker value={date} onChange={setDate} />
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button
                type="button"
                disabled={!date}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
              >
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "time" && (
          <section className="flex flex-col gap-4">
            <TimeSlotSelector slot={timeSlot} specificTime={specificTime} onSlotChange={setTimeSlot} onTimeChange={setSpecificTime} />
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button
                type="button"
                disabled={!timeSlot || !specificTime}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
              >
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "people" && (
          <section className="flex flex-col gap-6">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">請問幾位用餐？</p>
            <PeopleCounter value={people} onChange={setPeople} />
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button type="button" onClick={goNext} className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)]">
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "contact" && (
          <section className="flex flex-col gap-4">
            <ReservationContactForm name={contactName} phone={phone} onNameChange={setContactName} onPhoneChange={setPhone} />
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button
                type="button"
                disabled={!contactName.trim() || !phone}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
              >
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "premium" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">請問需要指定餐廳或高級訂位服務嗎？</p>
            <PremiumToggle value={isPremium} onChange={setIsPremium} />
            <div className="flex gap-3">
              <button type="button" onClick={goBack} className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand">
                上一步
              </button>
              <button
                type="button"
                disabled={isPremium === null}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
              >
                下一步
              </button>
            </div>
          </section>
        )}

        {step === "summary" && selectedRestaurant && (
          <ReservationSummaryCard
            data={{
              restaurantName: selectedRestaurant.name,
              date,
              timeSlot: timeSlot === "LUNCH" ? "午餐" : "晚餐",
              specificTime,
              people,
              contactName,
              phone,
              isPremium: Boolean(isPremium),
            }}
            onConfirm={handleConfirm}
            onEdit={goBack}
            submitting={submitting}
          />
        )}
      </main>

      <Toast text={toastText} onHide={() => setToastText(null)} />
      <ButlerLauncher currentPageId="reservation_flow" />
    </>
  );
}
