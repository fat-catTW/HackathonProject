import { useState } from "react";
import type { ClinicChatRecommendation } from "../types/clinic";
import type { ChatEvent } from "../types/request";
import { ChatRestaurantCardList } from "./ChatRestaurantCardList";
import { ClinicCardList } from "./ClinicCardList";
import { Mascot } from "./Mascot";
import { ShareWithFamilyButton } from "./ShareWithFamilyButton";
import { TaskCardList } from "./TaskCardList";

/**
 * 對話氣泡。屬於資料型元件，依 Requirement 15.3 維持不透明實色，不套玻璃擬態，
 * 避免長對話中文字疊在半透明背景上而降低可讀性（漸層仍為不透明色，不受此限）。
 *
 * 配色引用語意色 Token（Requirement 6.6），Light/Dark 共用同一份 className：
 * - 使用者氣泡：`.bg-bubble-user`（紫→桃紅／紫→紫的不透明漸層）+ `--color-on-primary` 字
 * - 助理氣泡：不透明 `--color-surface` 底 + `--color-foreground` 字，左側附小型 Mascot 頭像
 *   （對應聊天機器人 App 參考稿每則助理訊息前的機器人頭像）
 */
export function ChatMessage({
  event,
  onRedirectClick,
  onRestaurantSelect,
  onClinicContinue,
}: {
  event: ChatEvent;
  onRedirectClick?: (path: string) => void;
  onRestaurantSelect?: (name: string) => void;
  onClinicContinue?: (recommendation: ClinicChatRecommendation, clinicId: string) => void;
}) {
  const isUser = event.role === "USER";
  const recommendation = event.clinicRecommendation;
  const [selectedClinicId, setSelectedClinicId] = useState<string | null>(
    recommendation?.recommended_clinic_id ?? recommendation?.clinics[0]?.id ?? null,
  );

  return (
    <div className={`flex items-end gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <span
          aria-hidden
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-[var(--color-tertiary-soft)]"
        >
          <Mascot size={20} tone="brand" />
        </span>
      )}
      <div
        className={`max-w-[78%] whitespace-pre-line rounded-2xl px-4 py-3 leading-relaxed ${
          isUser
            ? "bg-bubble-user rounded-br-md text-[var(--color-on-primary)]"
            : "rounded-bl-md bg-[var(--color-surface)] text-[var(--color-foreground)] shadow-sm"
        }`}
      >
        {event.content}
        {event.taskCards && event.taskCards.length > 0 && <TaskCardList cards={event.taskCards} />}
        {event.restaurantCards && event.restaurantCards.length > 0 && (
          <ChatRestaurantCardList
            restaurants={event.restaurantCards}
            onSelect={(name) => onRestaurantSelect?.(name)}
          />
        )}
        {event.shareText && <ShareWithFamilyButton text={event.shareText} />}
        {event.redirectPath && (
          <button
            type="button"
            onClick={() => onRedirectClick?.(event.redirectPath!)}
            className="mt-3 block min-h-[44px] w-full rounded-2xl bg-[var(--color-primary)] px-4 py-2.5 text-base font-bold text-[var(--color-on-primary)]"
          >
            查看完整比價 →
          </button>
        )}
        {recommendation && (
          <div className="mt-3">
            <ClinicCardList
              clinics={recommendation.clinics}
              selectedId={selectedClinicId}
              recommendedId={recommendation.recommended_clinic_id}
              recommendReason={recommendation.recommend_reason}
              onSelect={setSelectedClinicId}
            />
            <button
              type="button"
              disabled={!selectedClinicId}
              onClick={() => selectedClinicId && onClinicContinue?.(recommendation, selectedClinicId)}
              className="mt-3 block min-h-[44px] w-full rounded-2xl bg-[var(--color-primary)] px-4 py-2.5 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
            >
              選這間，繼續掛號 →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
