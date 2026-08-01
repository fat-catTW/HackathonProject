import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { getProduct, recommendProducts } from "../api/health";
import { ApiError } from "../api/client";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { ServiceIcon } from "../components/ServiceIcon";
import { Toast } from "../components/Toast";
import { VoiceButton } from "../components/VoiceButton";
import { useSpeechRecognition } from "../hooks/useSpeechRecognition";
import type { HealthProduct, HealthRecommendationItem } from "../types/health";

export function HealthRecommendationPage() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [recommendations, setRecommendations] = useState<HealthRecommendationItem[] | null>(null);
  const [fallbackUsed, setFallbackUsed] = useState(false);
  const [toastText, setToastText] = useState<string | null>(null);
  const [selectedProduct, setSelectedProduct] = useState<HealthProduct | null>(null);
  const [loadingProductId, setLoadingProductId] = useState<string | null>(null);

  async function search(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;
    setQuery(trimmed);
    setLoading(true);
    setSelectedProduct(null);
    try {
      const result = await recommendProducts(trimmed);
      setRecommendations(result.recommendations);
      setFallbackUsed(result.fallback_used);
    } catch (error) {
      setToastText(error instanceof ApiError ? error.message : "查詢失敗，請稍後再試");
    } finally {
      setLoading(false);
    }
  }

  async function viewProduct(productId: string) {
    setLoadingProductId(productId);
    try {
      const product = await getProduct(productId);
      setSelectedProduct(product);
    } catch (error) {
      setToastText(error instanceof ApiError ? error.message : "查詢商品資訊失敗");
    } finally {
      setLoadingProductId(null);
    }
  }

  const speech = useSpeechRecognition((text) => void search(text));

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
          <h1 className="text-xl font-black text-[var(--color-foreground)]">健康商品推薦</h1>
        </header>

        <section className="rounded-[24px] border border-[var(--color-border)] bg-[var(--color-surface)] p-5 shadow-sm">
          <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">
            請說出你的健康或飲食需求
          </p>
          <p className="mt-2 text-sm leading-6 text-[var(--color-muted-foreground)]">
            例如：我在減脂但想吃點甜食、想找低鈉的鮮食、素食高蛋白選項
          </p>

          <form
            className="mt-4 flex items-center gap-3"
            onSubmit={(e) => {
              e.preventDefault();
              void search(query);
            }}
          >
            <VoiceButton
              listening={speech.listening}
              supported={speech.supported}
              onStart={speech.start}
              onStop={speech.stop}
            />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={speech.listening ? "正在聆聽，請直接說出需求" : "輸入你的健康或飲食需求"}
              aria-label="健康或飲食需求"
              className="min-w-0 flex-1 rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] px-4 py-3.5 outline-none focus:border-brand"
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="min-h-[44px] rounded-2xl bg-brand px-5 py-3.5 font-bold text-[var(--color-on-primary)] disabled:opacity-40"
            >
              查詢
            </button>
          </form>
        </section>

        {loading && (
          <p className="mt-6 text-center text-sm text-[var(--color-muted-foreground)]">正在為你尋找推薦商品…</p>
        )}

        {!loading && recommendations && recommendations.length === 0 && (
          <p className="mt-6 text-center text-sm leading-7 text-[var(--color-muted-foreground)]">
            很抱歉，目前沒有找到符合這個需求的商品，要不要換個方式描述？
          </p>
        )}

        {!loading && recommendations && recommendations.length > 0 && (
          <section className="mt-6 flex flex-col gap-3">
            {fallbackUsed && (
              <p className="rounded-2xl bg-[var(--color-warning-soft)] px-4 py-3 text-sm leading-6 text-[var(--color-warning)]">
                這次是用關鍵字比對挑選的，僅供參考。
              </p>
            )}
            {recommendations.map((rec) => {
              const hasDetails = rec.source === undefined || rec.source === "internal";
              const cardContent = (
                <>
                  <p className="text-base font-black text-[var(--color-foreground)]">{rec.name}</p>
                  <p className="mt-1 text-sm leading-6 text-[var(--color-muted-foreground)]">{rec.reason}</p>
                  {rec.match_tags.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {rec.match_tags.map((tag) => (
                        <span
                          key={tag}
                          className="rounded-full bg-brand-soft px-2.5 py-0.5 text-xs font-bold text-brand"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              );

              if (!hasDetails) {
                return (
                  <div
                    key={rec.product_id}
                    className="rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4"
                  >
                    {cardContent}
                  </div>
                );
              }

              return (
                <button
                  key={rec.product_id}
                  type="button"
                  onClick={() => void viewProduct(rec.product_id)}
                  disabled={loadingProductId === rec.product_id}
                  className="min-h-[44px] rounded-2xl border-2 border-[var(--color-border)] bg-[var(--color-surface)] p-4 text-left transition hover:border-brand disabled:opacity-60"
                >
                  {cardContent}
                </button>
              );
            })}
          </section>
        )}

        {selectedProduct && (
          <section className="mt-6 rounded-[24px] border-2 border-brand bg-[var(--color-surface)] p-5 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-black text-[var(--color-foreground)]">{selectedProduct.name}</h2>
              <span className="text-sm font-bold text-brand">${selectedProduct.price}</span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-sm text-[var(--color-muted-foreground)]">
              <p>熱量：{selectedProduct.calories} kcal</p>
              <p>蛋白質：{selectedProduct.protein_g} g</p>
              <p>碳水：{selectedProduct.carbs_g} g</p>
              <p>脂肪：{selectedProduct.fat_g} g</p>
              <p>鈉：{selectedProduct.sodium_mg} mg</p>
            </div>
            {selectedProduct.allergens.length > 0 && (
              <p className="mt-3 text-sm text-[var(--color-muted-foreground)]">
                過敏原：{selectedProduct.allergens.join("、")}
              </p>
            )}
          </section>
        )}
      </main>

      <Toast text={toastText} onHide={() => setToastText(null)} />
      <ButlerLauncher currentPageId="health_recommendation_flow" />
    </>
  );
}
