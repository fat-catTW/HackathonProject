import { useEffect, useMemo, useState } from "react";
import { ButlerLauncher } from "../components/ButlerLauncher";
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
}

export function ShopFlowPage() {
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
        { sku_id: matchedSku.sku_id, productName: activeProduct.name, attributesLabel, unitPrice: matchedSku.unit_price, quantity: 1 },
      ];
    });
    setToastText(`已加入購物車：${activeProduct.name}`);
  }

  function removeFromCart(skuId: string) {
    setCart((prev) => prev.filter((line) => line.sku_id !== skuId));
  }

  const cartTotal = cart.reduce((sum, line) => sum + line.unitPrice * line.quantity, 0);
  const hasPhysicalItem = cart.some((line) => products.find((p) => p.skus.some((s) => s.sku_id === line.sku_id))?.product_type === "PHYSICAL");
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
    <div className="shop-flow-page">
      {step === "store" && (
        <section>
          <h2>選擇店家</h2>
          {stores.map((store) => (
            <button
              key={store.id}
              onClick={() => {
                setSelectedStoreId(store.id);
                goNext();
              }}
            >
              {store.name}（{store.category}）
            </button>
          ))}
        </section>
      )}

      {step === "product" && (
        <section>
          <h2>選擇商品</h2>
          {products.map((product) => (
            <div key={product.id}>
              <button
                onClick={() => {
                  setActiveProduct(product);
                  setSelectedSpecs({});
                }}
              >
                {product.name} — NT${product.skus[0]?.unit_price}
              </button>
            </div>
          ))}
          {activeProduct && (
            <div>
              <h3>{activeProduct.name}</h3>
              <p>{activeProduct.description}</p>
              {activeProduct.specs.map((spec) => (
                <div key={spec.name}>
                  <span>{spec.name}：</span>
                  {spec.options.map((option) => (
                    <button
                      key={option}
                      onClick={() => setSelectedSpecs((prev) => ({ ...prev, [spec.name]: option }))}
                      aria-pressed={selectedSpecs[spec.name] === option}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              ))}
              <button disabled={!matchedSku} onClick={addToCart}>
                加入購物車{matchedSku ? `（NT$${matchedSku.unit_price}）` : ""}
              </button>
            </div>
          )}
          <button onClick={goNext} disabled={cart.length === 0}>
            前往購物車（{cart.length}）
          </button>
          <button onClick={goBack}>返回選店家</button>
        </section>
      )}

      {step === "cart" && (
        <section>
          <h2>購物車</h2>
          {cart.map((line) => (
            <div key={line.sku_id}>
              <span>
                {line.productName}（{line.attributesLabel || "單一規格"}）x{line.quantity} — NT${line.unitPrice * line.quantity}
              </span>
              <button onClick={() => removeFromCart(line.sku_id)}>移除</button>
            </div>
          ))}
          <p>小計：NT${cartTotal}</p>
          <button onClick={goBack}>繼續選購</button>
          <button onClick={goNext} disabled={cart.length === 0}>
            前往結帳
          </button>
        </section>
      )}

      {step === "checkout" && (
        <section>
          <h2>結帳</h2>
          <label>
            聯絡人姓名
            <input value={contactName} onChange={(e) => setContactName(e.target.value)} />
          </label>
          <label>
            聯絡電話
            <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="09XXXXXXXX" />
          </label>
          {hasPhysicalItem && (
            <>
              <label>
                收件城市
                <input value={address.city} onChange={(e) => setAddress((a) => ({ ...a, city: e.target.value }))} />
              </label>
              <label>
                收件地址
                <input value={address.street} onChange={(e) => setAddress((a) => ({ ...a, street: e.target.value }))} />
              </label>
            </>
          )}
          <p>
            可用點數：{pointsBalance}（最多可折抵 {maxUsablePoints} 點）
          </p>
          <label>
            使用點數折抵
            <input
              type="number"
              min={0}
              max={maxUsablePoints}
              value={usedPoints}
              onChange={(e) => setUsedPoints(Math.max(0, Math.min(maxUsablePoints, Number(e.target.value) || 0)))}
            />
          </label>
          <p>商品金額：NT${cartTotal}</p>
          <p>運費：NT${shippingFee}</p>
          <p>點數折抵：-NT${Math.min(usedPoints, maxUsablePoints)}</p>
          <p>應付金額：NT${orderTotal}</p>
          <button onClick={goBack}>返回購物車</button>
          <button onClick={handleSubmit} disabled={submitting || !contactName || !phone}>
            {submitting ? "送出中…" : "確認送出"}
          </button>
        </section>
      )}

      {step === "result" && result && (
        <section>
          <h2>訂單完成</h2>
          <p>訂單編號：{result.request_id}</p>
          <p>應付金額：NT${result.total_amount}</p>
          <p>本次獲得點數：{result.points_earned}</p>
          {Object.entries(result.redemption_codes).length > 0 && (
            <div>
              <h3>兌換碼</h3>
              {Object.entries(result.redemption_codes).map(([skuId, codes]) => (
                <div key={skuId}>
                  <span>{skuId}：</span>
                  {codes.map((code) => (
                    <code key={code}>{code}</code>
                  ))}
                </div>
              ))}
            </div>
          )}
          {order && (
            <>
              <p>目前狀態：{order.status}</p>
              {order.status !== "COMPLETED" && order.status !== "CANCELLED" && (
                <>
                  <button onClick={handleSimulateAdvance}>Demo：推進下一個狀態</button>
                  <button onClick={handleCancel}>取消訂單</button>
                </>
              )}
            </>
          )}
        </section>
      )}

      <Toast text={toastText} onHide={() => setToastText(null)} />
      <ButlerLauncher currentPageId="shop_flow" />
    </div>
  );
}
