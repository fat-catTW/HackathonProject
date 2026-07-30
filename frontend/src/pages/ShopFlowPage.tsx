import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { ServiceIcon } from "../components/ServiceIcon";
import { Toast } from "../components/Toast";
import {
  cancelShopOrder,
  getShopOrder,
  getShopPoints,
  listShopProducts,
  listShopStores,
  simulateShopOrderProgress,
  submitShopOrder,
} from "../api/shop";
import type { ShopCartLine, ShopOrder, ShopProduct, ShopStore, ShopSubmitResult } from "../types/shop";

type Step = "store" | "product" | "cart" | "checkout" | "result";
const STEP_ORDER: Step[] = ["store", "product", "cart", "checkout", "result"];

interface CartEntry {
  sku_id: string;
  productName: string;
  attributesLabel: string;
  unitPrice: number;
  quantity: number;
  productType: "PHYSICAL" | "SERIAL_CODE";
}

export function ShopFlowPage() {
  const navigate = useNavigate();
  const [stepIndex, setStepIndex] = useState(0);
  const step = STEP_ORDER[stepIndex];

  const [stores, setStores] = useState<ShopStore[]>([]);
  const [selectedStoreId, setSelectedStoreId] = useState<string | null>(null);
  const [products, setProducts] = useState<ShopProduct[]>([]);
  const [activeProduct, setActiveProduct] = useState<ShopProduct | null>(null);
  const [selectedSpecs, setSelectedSpecs] = useState<Record<string, string>>({});

  const [cart, setCart] = useState<CartEntry[]>([]);
  const [pointsBalance, setPointsBalance] = useState(0);
  const [usedPoints, setUsedPoints] = useState(0);
  const [contactName, setContactName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState({ city: "", street: "", contact_name: "", remark: "" });

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<ShopSubmitResult | null>(null);
  const [order, setOrder] = useState<ShopOrder | null>(null);
  const [toastText, setToastText] = useState<string | null>(null);

  useEffect(() => {
    listShopStores().then((res) => setStores(res.stores)).catch(() => setToastText("店家清單載入失敗"));
    getShopPoints().then((res) => setPointsBalance(res.balance)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedStoreId) return;
    listShopProducts(selectedStoreId).then((res) => setProducts(res.products)).catch(() => setToastText("商品清單載入失敗"));
  }, [selectedStoreId]);

  useEffect(() => {
    if (step !== "result" || !result || result.status === "COMPLETED") return;
    const interval = setInterval(() => {
      getShopOrder(result.request_id)
        .then((o) => {
          setOrder(o);
          if (o.status === "COMPLETED" || o.status === "CANCELLED") clearInterval(interval);
        })
        .catch(() => {});
    }, 5000);
    return () => clearInterval(interval);
  }, [step, result]);

  const goNext = () => setStepIndex((i) => Math.min(i + 1, STEP_ORDER.length - 1));
  const goBack = () => setStepIndex((i) => Math.max(i - 1, 0));

  const matchedSku = useMemo(() => {
    if (!activeProduct) return null;
    return activeProduct.skus.find((sku) =>
      Object.entries(sku.attributes).every(([name, value]) => selectedSpecs[name] === value),
    ) ?? (activeProduct.specs.length === 0 ? activeProduct.skus[0] : null);
  }, [activeProduct, selectedSpecs]);

  function addToCart() {
    if (!activeProduct || !matchedSku) return;
    const attributesLabel = Object.values(matchedSku.attributes).join(" / ");
    setCart((prev) => {
      const existing = prev.find((line) => line.sku_id === matchedSku.sku_id);
      if (existing) {
        return prev.map((line) => (line.sku_id === matchedSku.sku_id ? { ...line, quantity: line.quantity + 1 } : line));
      }
      return [
        ...prev,
        {
          sku_id: matchedSku.sku_id,
          productName: activeProduct.name,
          attributesLabel,
          unitPrice: matchedSku.unit_price,
          quantity: 1,
          productType: activeProduct.product_type,
        },
      ];
    });
    setToastText(`已加入購物車：${activeProduct.name}`);
  }

  function removeFromCart(skuId: string) {
    setCart((prev) => prev.filter((line) => line.sku_id !== skuId));
  }

  const cartTotal = cart.reduce((sum, line) => sum + line.unitPrice * line.quantity, 0);
  const hasPhysicalItem = cart.some((line) => line.productType === "PHYSICAL");
  const shippingFee = hasPhysicalItem ? 60 : 0;
  const payableBeforePoints = cartTotal + shippingFee;
  const maxUsablePoints = Math.min(pointsBalance, payableBeforePoints);
  const orderTotal = payableBeforePoints - Math.min(usedPoints, maxUsablePoints);

  async function handleSubmit() {
    setSubmitting(true);
    try {
      const cartLines: ShopCartLine[] = cart.map((line) => ({ sku_id: line.sku_id, quantity: line.quantity }));
      const submitted = await submitShopOrder({
        cart: cartLines,
        contact_name: contactName,
        phone,
        address: hasPhysicalItem ? { ...address, contact_name: contactName } : undefined,
        used_points: Math.min(usedPoints, maxUsablePoints),
      });
      setResult(submitted);
      const fullOrder = await getShopOrder(submitted.request_id);
      setOrder(fullOrder);
      goNext();
    } catch {
      setToastText("送出訂單失敗，請稍後再試");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleCancel() {
    if (!result) return;
    try {
      await cancelShopOrder(result.request_id);
      const fullOrder = await getShopOrder(result.request_id);
      setOrder(fullOrder);
      setToastText("訂單已取消");
    } catch {
      setToastText("取消失敗");
    }
  }

  async function handleSimulateAdvance() {
    if (!result) return;
    try {
      await simulateShopOrderProgress(result.request_id);
      const fullOrder = await getShopOrder(result.request_id);
      setOrder(fullOrder);
    } catch {
      setToastText("模擬推進失敗");
    }
  }

  return (
    <>
      <main className="mx-auto min-h-dvh max-w-md bg-canvas px-5 pb-32 pt-8">
        <header className="flex items-center gap-3 pb-4">
          <button
            type="button"
            onClick={() => navigate("/home")}
            aria-label="返回"
            className="flex h-11 w-11 items-center justify-center text-gray-500"
          >
            <ServiceIcon type="back" size={22} />
          </button>
          <h1 className="text-xl font-black text-slate-900">商城購物</h1>
        </header>

        {/* ====== Step 1: Store Selection ====== */}
        {step === "store" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">請選擇店家</p>
            <div className="flex flex-col gap-3">
              {stores.map((store) => (
                <button
                  key={store.id}
                  type="button"
                  onClick={() => {
                    setSelectedStoreId(store.id);
                    goNext();
                  }}
                  className="rounded-2xl border-2 border-slate-200 p-4 text-left transition hover:border-slate-300"
                >
                  <p className="text-base font-bold text-slate-900">{store.name}</p>
                  <p className="text-sm text-slate-500">{store.category}</p>
                </button>
              ))}
            </div>
          </section>
        )}

        {/* ====== Step 2: Product Selection ====== */}
        {step === "product" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">請選擇商品</p>
            <div className="flex flex-col gap-3">
              {products.map((product) => (
                <button
                  key={product.id}
                  type="button"
                  onClick={() => {
                    setActiveProduct(product);
                    setSelectedSpecs({});
                  }}
                  className={`rounded-2xl border-2 p-4 text-left transition ${
                    activeProduct?.id === product.id
                      ? "border-brand bg-brand/5"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <p className="text-base font-bold text-slate-900">{product.name}</p>
                  <p className="text-sm text-slate-500">NT${product.skus[0]?.unit_price}</p>
                </button>
              ))}
            </div>

            {activeProduct && (
              <div className="flex flex-col gap-3 rounded-xl border border-slate-200 p-4">
                <div>
                  <p className="text-base font-bold text-slate-900">{activeProduct.name}</p>
                  <p className="text-sm text-slate-500">{activeProduct.description}</p>
                </div>
                {activeProduct.specs.map((spec) => (
                  <div key={spec.name} className="flex flex-col gap-2">
                    <span className="text-sm text-slate-600">{spec.name}</span>
                    <div className="flex flex-wrap gap-2">
                      {spec.options.map((option) => (
                        <button
                          key={option}
                          type="button"
                          onClick={() => setSelectedSpecs((prev) => ({ ...prev, [spec.name]: option }))}
                          aria-pressed={selectedSpecs[spec.name] === option}
                          className={`rounded-full border-2 px-4 py-2 text-sm transition ${
                            selectedSpecs[spec.name] === option
                              ? "border-brand bg-brand/5 text-brand"
                              : "border-slate-200 text-slate-600 hover:border-slate-300"
                          }`}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
                <button
                  type="button"
                  disabled={!matchedSku}
                  onClick={addToCart}
                  className="min-h-[44px] rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
                >
                  加入購物車{matchedSku ? `（NT$${matchedSku.unit_price}）` : ""}
                </button>
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={goBack}
                className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
              >
                返回選店家
              </button>
              <button
                type="button"
                onClick={goNext}
                disabled={cart.length === 0}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
              >
                前往購物車（{cart.length}）
              </button>
            </div>
          </section>
        )}

        {/* ====== Step 3: Cart ====== */}
        {step === "cart" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">購物車</p>
            <div className="flex flex-col gap-2">
              {cart.map((line) => (
                <div
                  key={line.sku_id}
                  className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
                >
                  <span className="text-sm text-slate-600">
                    {line.productName}（{line.attributesLabel || "單一規格"}）x{line.quantity} — NT$
                    {line.unitPrice * line.quantity}
                  </span>
                  <button
                    type="button"
                    onClick={() => removeFromCart(line.sku_id)}
                    className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-300 text-slate-600"
                    aria-label="移除"
                  >
                    −
                  </button>
                </div>
              ))}
            </div>
            <div className="rounded-xl bg-slate-50 p-4">
              <div className="flex justify-between border-t border-slate-200 pt-2 text-base font-bold text-slate-900">
                <span>小計</span>
                <span>NT${cartTotal}</span>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={goBack}
                className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
              >
                繼續選購
              </button>
              <button
                type="button"
                onClick={goNext}
                disabled={cart.length === 0}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
              >
                前往結帳
              </button>
            </div>
          </section>
        )}

        {/* ====== Step 4: Checkout ====== */}
        {step === "checkout" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">結帳</p>
            <div className="flex flex-col gap-3">
              <label className="flex flex-col gap-1">
                <span className="text-sm text-slate-600">聯絡人姓名</span>
                <input
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                  className="rounded-xl border border-slate-300 px-4 py-3 text-base"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-sm text-slate-600">聯絡電話</span>
                <input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="09XXXXXXXX"
                  className="rounded-xl border border-slate-300 px-4 py-3 text-base"
                />
              </label>
              {hasPhysicalItem && (
                <>
                  <label className="flex flex-col gap-1">
                    <span className="text-sm text-slate-600">收件城市</span>
                    <input
                      value={address.city}
                      onChange={(e) => setAddress((a) => ({ ...a, city: e.target.value }))}
                      className="rounded-xl border border-slate-300 px-4 py-3 text-base"
                    />
                  </label>
                  <label className="flex flex-col gap-1">
                    <span className="text-sm text-slate-600">收件地址</span>
                    <input
                      value={address.street}
                      onChange={(e) => setAddress((a) => ({ ...a, street: e.target.value }))}
                      className="rounded-xl border border-slate-300 px-4 py-3 text-base"
                    />
                  </label>
                </>
              )}
            </div>

            <div className="flex flex-col gap-3 rounded-xl border border-slate-200 p-4">
              <p className="text-sm text-slate-600">
                可用點數：{pointsBalance}（最多可折抵 {maxUsablePoints} 點）
              </p>
              <label className="flex flex-col gap-1">
                <span className="text-sm text-slate-600">使用點數折抵</span>
                <input
                  type="number"
                  min={0}
                  max={maxUsablePoints}
                  value={usedPoints}
                  onChange={(e) => setUsedPoints(Math.max(0, Math.min(maxUsablePoints, Number(e.target.value) || 0)))}
                  className="rounded-xl border border-slate-300 px-4 py-3 text-base"
                />
              </label>
            </div>

            <div className="rounded-xl bg-slate-50 p-4">
              <div className="flex justify-between text-sm text-slate-600">
                <span>商品金額</span>
                <span>NT${cartTotal}</span>
              </div>
              <div className="flex justify-between text-sm text-slate-600">
                <span>運費</span>
                <span>NT${shippingFee}</span>
              </div>
              <div className="flex justify-between text-sm text-slate-600">
                <span>點數折抵</span>
                <span>-NT${Math.min(usedPoints, maxUsablePoints)}</span>
              </div>
              <div className="mt-1 flex justify-between border-t border-slate-200 pt-2 text-base font-bold text-slate-900">
                <span>應付金額</span>
                <span>NT${orderTotal}</span>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={goBack}
                className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
              >
                返回購物車
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={submitting || !contactName || !phone}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
              >
                {submitting ? "送出中…" : "確認送出"}
              </button>
            </div>
          </section>
        )}

        {/* ====== Step 5: Result ====== */}
        {step === "result" && result && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">訂單完成</p>

            <div className="rounded-xl border border-brand/30 bg-brand/5 p-4">
              <p className="text-sm text-slate-600">訂單編號：{result.request_id}</p>
              <p className="text-sm text-slate-600">應付金額：NT${result.total_amount}</p>
              <p className="text-sm font-semibold text-brand">本次獲得點數：{result.points_earned}</p>
            </div>

            {Object.entries(result.redemption_codes).length > 0 && (
              <div className="flex flex-col gap-2 rounded-xl border border-slate-200 p-4">
                <p className="text-sm font-bold text-slate-700">兌換碼</p>
                {Object.entries(result.redemption_codes).map(([skuId, codes]) => (
                  <div key={skuId} className="flex flex-col gap-1">
                    <span className="text-sm text-slate-600">{skuId}</span>
                    <div className="flex flex-wrap gap-2">
                      {codes.map((code) => (
                        <code key={code} className="rounded-lg bg-slate-100 px-3 py-2 font-mono text-sm">
                          {code}
                        </code>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {order && (
              <>
                <div className="rounded-xl bg-slate-50 p-4">
                  <p className="text-sm text-slate-600">目前狀態：{order.status}</p>
                </div>
                {order.status !== "COMPLETED" && order.status !== "CANCELLED" && (
                  <div className="flex gap-3">
                    <button
                      type="button"
                      onClick={handleCancel}
                      className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
                    >
                      取消訂單
                    </button>
                    <button
                      type="button"
                      onClick={handleSimulateAdvance}
                      className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white"
                    >
                      Demo：推進下一個狀態
                    </button>
                  </div>
                )}
              </>
            )}
          </section>
        )}
      </main>

      <Toast text={toastText} onHide={() => setToastText(null)} />
      <ButlerLauncher currentPageId="shop_flow" />
    </>
  );
}
