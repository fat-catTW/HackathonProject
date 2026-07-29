import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { ServiceIcon } from "../components/ServiceIcon";
import { Toast } from "../components/Toast";
import {
  getDeliveryOrder,
  getDeliveryStore,
  listDeliveryStores,
  submitDeliveryOrder,
} from "../api/delivery";
import type {
  CartItem,
  DeliveryAddress,
  DeliveryOrder,
  DeliveryStore,
  DeliveryStoreDetail,
  MenuItem,
} from "../types/delivery";

type Step = "address" | "store" | "menu" | "summary" | "tracking";
const STEP_ORDER: Step[] = ["address", "store", "menu", "summary", "tracking"];

export function DeliveryFlowPage() {
  const navigate = useNavigate();
  const [stores, setStores] = useState<DeliveryStore[]>([]);
  const [stepIndex, setStepIndex] = useState(0);

  // Address state
  const [address, setAddress] = useState<DeliveryAddress>({
    lat: 25.033,
    lng: 121.565,
    area: "",
    city: "台北市",
    street: "",
    remark: "",
    contact_name: "",
    phone: "",
  });

  // Store & menu state
  const [selectedStoreId, setSelectedStoreId] = useState<string | null>(null);
  const [storeDetail, setStoreDetail] = useState<DeliveryStoreDetail | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [note, setNote] = useState("");

  // Submission & tracking state
  const [submitting, setSubmitting] = useState(false);
  const [order, setOrder] = useState<DeliveryOrder | null>(null);
  const [toastText, setToastText] = useState<string | null>(null);

  const step = STEP_ORDER[stepIndex];
  const goNext = () => setStepIndex((i) => Math.min(i + 1, STEP_ORDER.length - 1));
  const goBack = () => setStepIndex((i) => Math.max(i - 1, 0));

  useEffect(() => {
    listDeliveryStores()
      .then(setStores)
      .catch(() => setToastText("無法載入店家清單，請稍後再試。"));
  }, []);

  // Load store detail when selected
  useEffect(() => {
    if (selectedStoreId) {
      getDeliveryStore(selectedStoreId)
        .then(setStoreDetail)
        .catch(() => setToastText("無法載入菜單，請重試。"));
    }
  }, [selectedStoreId]);

  // Poll order status when tracking
  useEffect(() => {
    if (step !== "tracking" || !order) return;
    const interval = setInterval(async () => {
      try {
        const updated = await getDeliveryOrder(order.request_id);
        setOrder(updated);
        if (updated.order_status === "70" || updated.order_status === "90") {
          clearInterval(interval);
        }
      } catch {
        /* ignore polling errors */
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [step, order]);

  function addToCart(item: MenuItem) {
    setCart((prev) => {
      const existing = prev.find((c) => c.id === item.id);
      if (existing) {
        return prev.map((c) =>
          c.id === item.id ? { ...c, quantity: c.quantity + 1 } : c
        );
      }
      return [
        ...prev,
        { id: item.id, title: item.title, quantity: 1, price: item.price, modifier_group: [] },
      ];
    });
  }

  function removeFromCart(itemId: string) {
    setCart((prev) =>
      prev
        .map((c) => (c.id === itemId ? { ...c, quantity: c.quantity - 1 } : c))
        .filter((c) => c.quantity > 0)
    );
  }

  const cartTotal = cart.reduce((sum, c) => sum + c.price * c.quantity, 0);
  const shippingFee = 60;
  const orderTotal = cartTotal + shippingFee;

  async function handleSubmit() {
    if (!selectedStoreId || !storeDetail) return;
    setSubmitting(true);
    try {
      const result = await submitDeliveryOrder({
        address,
        goods: cart,
        store_id: selectedStoreId,
        store_name: storeDetail.name,
        store_address: storeDetail.address,
        store_url: storeDetail.url,
        note,
        shipping_fee: shippingFee,
      });
      // Fetch full order for tracking
      const fullOrder = await getDeliveryOrder(result.request_id);
      setOrder(fullOrder);
      goNext(); // → tracking
    } catch (err) {
      setSubmitting(false);
      setToastText(err instanceof Error ? err.message : "訂單送出失敗，請重試。");
    }
  }

  const canSubmitAddress =
    address.contact_name.trim() && address.city.trim() && address.street.trim();

  return (
    <>
      <main className="mx-auto min-h-dvh max-w-md bg-canvas px-5 pb-32 pt-8">
        <header className="flex items-center gap-3 pb-4">
          <button
            type="button"
            onClick={() => (step === "tracking" ? navigate("/home") : navigate("/home"))}
            aria-label="返回"
            className="flex h-11 w-11 items-center justify-center text-gray-500"
          >
            <ServiceIcon type="back" size={22} />
          </button>
          <h1 className="text-xl font-black text-slate-900">美食外送</h1>
        </header>

        {/* ====== Step 1: Address ====== */}
        {step === "address" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">請輸入外送地址</p>
            <div className="flex flex-col gap-3">
              <label className="flex flex-col gap-1">
                <span className="text-sm text-slate-600">城市</span>
                <input
                  type="text"
                  value={address.city}
                  onChange={(e) => setAddress({ ...address, city: e.target.value })}
                  placeholder="例：台北市"
                  className="rounded-xl border border-slate-300 px-4 py-3 text-base"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-sm text-slate-600">區域</span>
                <input
                  type="text"
                  value={address.area}
                  onChange={(e) => setAddress({ ...address, area: e.target.value })}
                  placeholder="例：大安區"
                  className="rounded-xl border border-slate-300 px-4 py-3 text-base"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-sm text-slate-600">街道地址</span>
                <input
                  type="text"
                  value={address.street}
                  onChange={(e) => setAddress({ ...address, street: e.target.value })}
                  placeholder="例：忠孝東路四段100號"
                  className="rounded-xl border border-slate-300 px-4 py-3 text-base"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-sm text-slate-600">備註（樓層、門牌等）</span>
                <input
                  type="text"
                  value={address.remark}
                  onChange={(e) => setAddress({ ...address, remark: e.target.value })}
                  placeholder="例：8樓之2"
                  className="rounded-xl border border-slate-300 px-4 py-3 text-base"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-sm text-slate-600">收件人姓名</span>
                <input
                  type="text"
                  value={address.contact_name}
                  onChange={(e) => setAddress({ ...address, contact_name: e.target.value })}
                  placeholder="收件人姓名"
                  className="rounded-xl border border-slate-300 px-4 py-3 text-base"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-sm text-slate-600">聯絡電話（選填）</span>
                <input
                  type="tel"
                  value={address.phone || ""}
                  onChange={(e) => setAddress({ ...address, phone: e.target.value })}
                  placeholder="09xxxxxxxx"
                  className="rounded-xl border border-slate-300 px-4 py-3 text-base"
                />
              </label>
            </div>
            <button
              type="button"
              disabled={!canSubmitAddress}
              onClick={goNext}
              className="mt-2 min-h-[44px] rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
            >
              下一步：選擇店家
            </button>
          </section>
        )}

        {/* ====== Step 2: Store Selection ====== */}
        {step === "store" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">請選擇外送店家</p>
            <div className="flex flex-col gap-3">
              {stores.map((store) => (
                <button
                  key={store.id}
                  type="button"
                  onClick={() => {
                    setSelectedStoreId(store.id);
                    setCart([]);
                  }}
                  className={`rounded-2xl border-2 p-4 text-left transition ${
                    selectedStoreId === store.id
                      ? "border-brand bg-brand/5"
                      : "border-slate-200 hover:border-slate-300"
                  }`}
                >
                  <p className="text-base font-bold text-slate-900">{store.name}</p>
                  <p className="text-sm text-slate-500">{store.cuisine} · {store.address}</p>
                </button>
              ))}
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={goBack}
                className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
              >
                上一步
              </button>
              <button
                type="button"
                disabled={!selectedStoreId}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
              >
                選擇餐點
              </button>
            </div>
          </section>
        )}

        {/* ====== Step 3: Menu & Cart ====== */}
        {step === "menu" && storeDetail && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">
              {storeDetail.name} — 選擇餐點
            </p>

            {/* Menu items */}
            <div className="flex flex-col gap-2">
              {storeDetail.menu.map((item) => {
                const inCart = cart.find((c) => c.id === item.id);
                return (
                  <div
                    key={item.id}
                    className="flex items-center justify-between rounded-xl border border-slate-200 px-4 py-3"
                  >
                    <div>
                      <p className="text-base font-semibold text-slate-900">{item.title}</p>
                      <p className="text-sm text-slate-500">${item.price}</p>
                      {item.modifier_group.length > 0 && (
                        <p className="text-xs text-slate-400">
                          可加購：{item.modifier_group.map((g) => g.name).join("、")}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {inCart && (
                        <>
                          <button
                            type="button"
                            onClick={() => removeFromCart(item.id)}
                            className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-300 text-slate-600"
                            aria-label="減少數量"
                          >
                            −
                          </button>
                          <span className="w-6 text-center text-base font-bold">
                            {inCart.quantity}
                          </span>
                        </>
                      )}
                      <button
                        type="button"
                        onClick={() => addToCart(item)}
                        className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-white"
                        aria-label="加入購物車"
                      >
                        +
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Cart summary */}
            {cart.length > 0 && (
              <div className="rounded-xl bg-slate-50 p-4">
                <p className="text-sm font-bold text-slate-700">購物車（{cart.length} 項）</p>
                {cart.map((c) => (
                  <div key={c.id} className="flex justify-between text-sm text-slate-600">
                    <span>{c.title} x{c.quantity}</span>
                    <span>${c.price * c.quantity}</span>
                  </div>
                ))}
                <div className="mt-2 border-t border-slate-200 pt-2 text-sm">
                  <div className="flex justify-between text-slate-600">
                    <span>小計</span>
                    <span>${cartTotal}</span>
                  </div>
                  <div className="flex justify-between text-slate-600">
                    <span>外送費</span>
                    <span>${shippingFee}</span>
                  </div>
                  <div className="flex justify-between font-bold text-slate-900">
                    <span>合計</span>
                    <span>${orderTotal}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Note */}
            <label className="flex flex-col gap-1">
              <span className="text-sm text-slate-600">備註給店家（選填）</span>
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="例：不要辣、多加醬"
                className="rounded-xl border border-slate-300 px-4 py-3 text-base"
              />
            </label>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={goBack}
                className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
              >
                上一步
              </button>
              <button
                type="button"
                disabled={cart.length === 0}
                onClick={goNext}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
              >
                確認訂單
              </button>
            </div>
          </section>
        )}

        {/* ====== Step 4: Summary & Confirm ====== */}
        {step === "summary" && storeDetail && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">訂單確認</p>

            <div className="rounded-xl border border-slate-200 p-4">
              <p className="text-sm font-bold text-slate-700">外送地址</p>
              <p className="text-sm text-slate-600">
                {address.city}{address.area}{address.street}
                {address.remark && `（${address.remark}）`}
              </p>
              <p className="text-sm text-slate-600">收件人：{address.contact_name}</p>
              {address.phone && <p className="text-sm text-slate-600">電話：{address.phone}</p>}
            </div>

            <div className="rounded-xl border border-slate-200 p-4">
              <p className="text-sm font-bold text-slate-700">店家：{storeDetail.name}</p>
              {cart.map((c) => (
                <div key={c.id} className="flex justify-between text-sm text-slate-600">
                  <span>{c.title} x{c.quantity}</span>
                  <span>${c.price * c.quantity}</span>
                </div>
              ))}
              {note && <p className="mt-1 text-xs text-slate-400">備註：{note}</p>}
            </div>

            <div className="rounded-xl bg-slate-50 p-4">
              <div className="flex justify-between text-sm text-slate-600">
                <span>餐點小計</span>
                <span>${cartTotal}</span>
              </div>
              <div className="flex justify-between text-sm text-slate-600">
                <span>外送費</span>
                <span>${shippingFee}</span>
              </div>
              <div className="mt-1 flex justify-between border-t border-slate-200 pt-2 text-base font-bold text-slate-900">
                <span>應付金額</span>
                <span>${orderTotal}</span>
              </div>
            </div>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={goBack}
                className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
              >
                修改
              </button>
              <button
                type="button"
                disabled={submitting}
                onClick={handleSubmit}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-white disabled:opacity-40"
              >
                {submitting ? "送出中..." : "確認送出"}
              </button>
            </div>
          </section>
        )}

        {/* ====== Step 5: Tracking ====== */}
        {step === "tracking" && order && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-slate-900">外送進度追蹤</p>

            <div className="rounded-xl border border-brand/30 bg-brand/5 p-4">
              <p className="text-lg font-black text-brand">
                {order.order_status_label || "處理中"}
              </p>
              <p className="text-sm text-slate-600">訂單編號：{order.request_id}</p>
            </div>

            {/* Delivery driver info */}
            {order.vendor_data?.delivery && (
              <div className="rounded-xl border border-slate-200 p-4">
                <p className="text-sm font-bold text-slate-700">外送員資訊</p>
                <p className="text-sm text-slate-600">
                  姓名：{order.vendor_data.delivery.driver_name}
                </p>
                <p className="text-sm text-slate-600">
                  電話：{order.vendor_data.delivery.driver_phone}
                </p>
                <p className="text-sm font-semibold text-brand">
                  預計 {order.vendor_data.delivery.eta_minutes} 分鐘送達
                </p>
              </div>
            )}

            {/* Order details */}
            <div className="rounded-xl border border-slate-200 p-4">
              <p className="text-sm font-bold text-slate-700">
                {order.order_items.store.name}
              </p>
              {order.order_items.goods.map((g) => (
                <div key={g.id} className="flex justify-between text-sm text-slate-600">
                  <span>{g.title} x{g.quantity}</span>
                  <span>${g.price * g.quantity}</span>
                </div>
              ))}
              <div className="mt-2 border-t border-slate-200 pt-2 text-sm font-bold text-slate-900">
                合計 ${order.total_amount}
              </div>
            </div>

            {/* Status progress bar */}
            <div className="rounded-xl bg-slate-50 p-4">
              <p className="mb-2 text-sm font-bold text-slate-700">配送狀態</p>
              <div className="flex items-center gap-1">
                {["01", "02", "03", "04", "05", "70"].map((s) => (
                  <div
                    key={s}
                    className={`h-2 flex-1 rounded-full ${
                      s <= order.order_status ? "bg-brand" : "bg-slate-200"
                    }`}
                  />
                ))}
              </div>
              <div className="mt-1 flex justify-between text-xs text-slate-400">
                <span>待接單</span>
                <span>已送達</span>
              </div>
            </div>

            <button
              type="button"
              onClick={() => navigate("/home")}
              className="mt-2 min-h-[44px] rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
            >
              返回首頁
            </button>
          </section>
        )}
      </main>

      <Toast text={toastText} onHide={() => setToastText(null)} />
      <ButlerLauncher currentPageId="delivery_flow" />
    </>
  );
}
