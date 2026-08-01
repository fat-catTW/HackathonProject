import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { ButlerLauncher } from "../components/ButlerLauncher";
import { GlassPanel } from "../components/GlassPanel";
import { RatingStars } from "../components/RatingStars";
import { ServiceIcon } from "../components/ServiceIcon";
import { Toast } from "../components/Toast";
import {
  cancelShopOrder,
  getShopCompareGroup,
  getShopOrder,
  getShopPoints,
  getShopProductReviews,
  listShopCategories,
  listShopProducts,
  submitShopOrder,
} from "../api/shop";
import type { ShopCartLine, ShopCategory, ShopOrder, ShopProduct, ShopReview, ShopSubmitResult } from "../types/shop";

type Step = "category" | "product" | "cart" | "checkout" | "result";
const STEP_ORDER: Step[] = ["category", "product", "cart", "checkout", "result"];

interface CartEntry {
  sku_id: string;
  storeId: string;
  storeName: string;
  productName: string;
  attributesLabel: string;
  unitPrice: number;
  quantity: number;
  productType: "PHYSICAL" | "SERIAL_CODE";
}

interface ProductGroup {
  groupKey: string;
  offers: (ShopProduct & { min_unit_price: number })[];
}

export function ShopFlowPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [stepIndex, setStepIndex] = useState(0);
  const step = STEP_ORDER[stepIndex];

  const [categories, setCategories] = useState<ShopCategory[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(null);
  const [products, setProducts] = useState<ShopProduct[]>([]);
  const [activeProduct, setActiveProduct] = useState<ShopProduct | null>(null);
  const [comparingGroupId, setComparingGroupId] = useState<string | null>(null);
  const [selectedSpecs, setSelectedSpecs] = useState<Record<string, string>>({});
  const [sortByRating, setSortByRating] = useState(false);
  const [showReviews, setShowReviews] = useState(false);
  const [reviews, setReviews] = useState<ShopReview[]>([]);

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
    listShopCategories().then((res) => setCategories(res.categories)).catch(() => setToastText("商品類型載入失敗"));
    getShopPoints().then((res) => setPointsBalance(res.balance)).catch(() => {});
  }, []);

  const compareParam = searchParams.get("compare");

  useEffect(() => {
    if (!compareParam) return;
    getShopCompareGroup(compareParam)
      .then((group) => {
        setSelectedCategoryId(group.category_id);
        setComparingGroupId(group.group_id);
        setStepIndex(STEP_ORDER.indexOf("product"));
      })
      .catch(() => setToastText("比價資料載入失敗"));
  }, [compareParam]);

  const categoryIdParam = searchParams.get("category_id");

  useEffect(() => {
    if (!categoryIdParam) return;
    setSelectedCategoryId(categoryIdParam);
    setStepIndex(STEP_ORDER.indexOf("product"));
  }, [categoryIdParam]);

  useEffect(() => {
    if (!selectedCategoryId) return;
    setActiveProduct(null);
    setSelectedSpecs({});
    setPendingQuantity(1);
    listShopProducts(selectedCategoryId).then((res) => setProducts(res.products)).catch(() => setToastText("商品清單載入失敗"));
  }, [selectedCategoryId]);

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

  useEffect(() => {
    setShowReviews(false);
    setReviews([]);
  }, [activeProduct?.id]);

  useEffect(() => {
    if (!showReviews || !activeProduct) return;
    getShopProductReviews(activeProduct.id)
      .then((res) => setReviews(res.reviews))
      .catch(() => setToastText("評價載入失敗"));
  }, [showReviews, activeProduct]);

  const productGroups = useMemo<ProductGroup[]>(() => {
    const groups = new Map<string, (ShopProduct & { min_unit_price: number })[]>();
    for (const product of products) {
      const withPrice = { ...product, min_unit_price: Math.min(...product.skus.map((s) => s.unit_price)) };
      const key = product.compare_group_id ?? product.id;
      const existing = groups.get(key);
      if (existing) existing.push(withPrice);
      else groups.set(key, [withPrice]);
    }
    return Array.from(groups.entries()).map(([groupKey, offers]) => ({
      groupKey,
      offers: offers.sort((a, b) => a.min_unit_price - b.min_unit_price),
    }));
  }, [products]);

  const visibleGroups = useMemo(() => {
    if (!sortByRating) return productGroups;
    return [...productGroups].sort(
      (a, b) => Math.max(...b.offers.map((o) => o.rating_avg)) - Math.max(...a.offers.map((o) => o.rating_avg)),
    );
  }, [productGroups, sortByRating]);

  const comparingOffers = useMemo(() => {
    if (!comparingGroupId) return [];
    return productGroups.find((g) => g.groupKey === comparingGroupId)?.offers ?? [];
  }, [productGroups, comparingGroupId]);

  const [pendingQuantity, setPendingQuantity] = useState(1);

  function addToCart() {
    if (!activeProduct || !matchedSku) return;
    const attributesLabel = Object.values(matchedSku.attributes).join(" / ");
    const quantityToAdd = pendingQuantity;
    setCart((prev) => {
      const existing = prev.find((line) => line.sku_id === matchedSku.sku_id);
      if (existing) {
        return prev.map((line) =>
          line.sku_id === matchedSku.sku_id ? { ...line, quantity: line.quantity + quantityToAdd } : line,
        );
      }
      return [
        ...prev,
        {
          sku_id: matchedSku.sku_id,
          storeId: activeProduct.store_id,
          storeName: activeProduct.store_name,
          productName: activeProduct.name,
          attributesLabel,
          unitPrice: matchedSku.unit_price,
          quantity: quantityToAdd,
          productType: activeProduct.product_type,
        },
      ];
    });
    setToastText(`已加入購物車：${activeProduct.name} x${quantityToAdd}`);
    setPendingQuantity(1);
  }

  function removeFromCart(skuId: string) {
    setCart((prev) => prev.filter((line) => line.sku_id !== skuId));
  }

  function updateCartQuantity(skuId: string, quantity: number) {
    setCart((prev) =>
      quantity <= 0
        ? prev.filter((line) => line.sku_id !== skuId)
        : prev.map((line) => (line.sku_id === skuId ? { ...line, quantity } : line)),
    );
  }

  const cartGroups = useMemo(() => {
    const groups = new Map<string, { storeName: string; lines: CartEntry[] }>();
    for (const line of cart) {
      const existing = groups.get(line.storeId);
      if (existing) {
        existing.lines.push(line);
      } else {
        groups.set(line.storeId, { storeName: line.storeName, lines: [line] });
      }
    }
    return Array.from(groups.values());
  }, [cart]);

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
          <h1 className="text-xl font-black text-[var(--color-foreground)]">商城購物</h1>
        </header>

        {/* ====== Step 1: Category Selection ====== */}
        {step === "category" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">請選擇商品類型</p>
            <div className="flex flex-col gap-3">
              {categories.map((category) => (
                <button
                  key={category.id}
                  type="button"
                  onClick={() => {
                    setSelectedCategoryId(category.id);
                    setComparingGroupId(null);
                    goNext();
                  }}
                  className="rounded-2xl border-2 border-[var(--color-border)] p-4 text-left transition hover:border-[var(--color-primary)]"
                >
                  <p className="text-base font-bold text-[var(--color-foreground)]">{category.name}</p>
                </button>
              ))}
            </div>
          </section>
        )}

        {/* ====== Step 2: Product Selection ====== */}
        {step === "product" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">請選擇商品</p>
            <button
              type="button"
              onClick={() => setSortByRating((v) => !v)}
              aria-pressed={sortByRating}
              className={`self-start rounded-full border-2 px-4 py-2 text-sm font-bold transition ${
                sortByRating
                  ? "border-brand bg-brand/5 text-brand"
                  : "border-[var(--color-border)] text-[var(--color-muted-foreground)] hover:border-[var(--color-primary)]"
              }`}
            >
              依評分排序
            </button>
            <div className="flex flex-col gap-3">
              {visibleGroups.map((group) => {
                if (group.offers.length > 1) {
                  const prices = group.offers.map((o) => o.min_unit_price);
                  return (
                    <button
                      key={group.groupKey}
                      type="button"
                      onClick={() => {
                        setComparingGroupId(group.groupKey);
                        setActiveProduct(null);
                        setSelectedSpecs({});
                        setPendingQuantity(1);
                      }}
                      className="rounded-2xl border-2 border-[var(--color-border)] p-4 text-left transition hover:border-[var(--color-primary)]"
                    >
                      <p className="text-base font-bold text-[var(--color-foreground)]">{group.offers[0].name}</p>
                      <p className="text-sm text-[var(--color-muted-foreground)]">
                        NT${Math.min(...prices)}~{Math.max(...prices)}
                      </p>
                      <p className="text-xs text-[var(--color-muted-foreground)]">共 {group.offers.length} 家店販售</p>
                      <RatingStars rating={Math.max(...group.offers.map((o) => o.rating_avg))} />
                    </button>
                  );
                }
                const product = group.offers[0];
                return (
                  <button
                    key={group.groupKey}
                    type="button"
                    onClick={() => {
                      setActiveProduct(product);
                      setComparingGroupId(null);
                      setSelectedSpecs({});
                      setPendingQuantity(1);
                    }}
                    className={`rounded-2xl border-2 p-4 text-left transition ${
                      activeProduct?.id === product.id
                        ? "border-brand bg-brand/5"
                        : "border-[var(--color-border)] hover:border-[var(--color-primary)]"
                    }`}
                  >
                    <p className="text-base font-bold text-[var(--color-foreground)]">{product.name}</p>
                    <p className="text-sm text-[var(--color-muted-foreground)]">NT${product.skus[0]?.unit_price}</p>
                    <p className="text-xs text-[var(--color-muted-foreground)]">{product.store_name}</p>
                    <RatingStars rating={product.rating_avg} count={product.rating_count} />
                  </button>
                );
              })}
            </div>

            {comparingGroupId && (
              <div className="flex flex-col gap-3 rounded-xl border border-[var(--color-border)] p-4">
                <p className="text-base font-bold text-[var(--color-foreground)]">
                  {comparingOffers[0]?.name} 比價
                </p>
                {comparingOffers.map((offer, index) => (
                  <div
                    key={offer.id}
                    className="flex items-center justify-between rounded-xl border border-[var(--color-border)] px-4 py-3"
                  >
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-[var(--color-foreground)]">{offer.store_name}</span>
                        {index === 0 && (
                          <span className="rounded-full bg-[var(--color-success-soft)] px-2 py-0.5 text-xs font-bold text-[var(--color-success)]">
                            最便宜
                          </span>
                        )}
                      </div>
                      <RatingStars rating={offer.rating_avg} count={offer.rating_count} />
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-bold text-[var(--color-foreground)]">NT${offer.min_unit_price}</span>
                      <button
                        type="button"
                        onClick={() => {
                          setActiveProduct(offer);
                          setComparingGroupId(null);
                          setSelectedSpecs({});
                          setPendingQuantity(1);
                        }}
                        className="min-h-[44px] rounded-full bg-brand px-4 py-2 text-sm font-bold text-[var(--color-on-primary)]"
                      >
                        選這家
                      </button>
                    </div>
                  </div>
                ))}
                <button
                  type="button"
                  onClick={() => setComparingGroupId(null)}
                  className="text-sm text-[var(--color-muted-foreground)] underline"
                >
                  返回商品列表
                </button>
              </div>
            )}

            {activeProduct && (
              <div className="flex flex-col gap-3 rounded-xl border border-[var(--color-border)] p-4">
                <div>
                  <p className="text-base font-bold text-[var(--color-foreground)]">{activeProduct.name}</p>
                  <p className="text-sm text-[var(--color-muted-foreground)]">{activeProduct.description}</p>
                </div>
                {activeProduct.specs.map((spec) => (
                  <div key={spec.name} className="flex flex-col gap-2">
                    <span className="text-sm text-[var(--color-muted-foreground)]">{spec.name}</span>
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
                              : "border-[var(--color-border)] text-[var(--color-muted-foreground)] hover:border-[var(--color-primary)]"
                          }`}
                        >
                          {option}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
                <div className="flex items-center gap-3">
                  <span className="text-sm text-[var(--color-muted-foreground)]">數量</span>
                  <button
                    type="button"
                    onClick={() => setPendingQuantity((q) => Math.max(1, q - 1))}
                    className="flex h-8 w-8 items-center justify-center rounded-full border border-[var(--color-border)] text-[var(--color-muted-foreground)]"
                    aria-label="減少數量"
                  >
                    −
                  </button>
                  <span className="w-6 text-center text-base font-bold">{pendingQuantity}</span>
                  <button
                    type="button"
                    onClick={() => setPendingQuantity((q) => q + 1)}
                    className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-[var(--color-on-primary)]"
                    aria-label="增加數量"
                  >
                    +
                  </button>
                </div>
                <button
                  type="button"
                  disabled={!matchedSku}
                  onClick={addToCart}
                  className="min-h-[44px] rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
                >
                  加入購物車{matchedSku ? `（NT$${matchedSku.unit_price * pendingQuantity}）` : ""}
                </button>
                <button
                  type="button"
                  onClick={() => setShowReviews((v) => !v)}
                  className="text-sm font-bold text-brand underline"
                >
                  {showReviews ? "收合評價" : "查看評價"}
                </button>
                {showReviews && (
                  <div className="flex flex-col gap-3 rounded-xl bg-[var(--color-canvas)] p-3">
                    {reviews.length === 0 && (
                      <p className="text-sm text-[var(--color-muted-foreground)]">目前還沒有評價</p>
                    )}
                    {reviews.map((review) => (
                      <div
                        key={review.review_id}
                        className="flex flex-col gap-1 border-b border-[var(--color-border)] pb-2 last:border-b-0 last:pb-0"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-bold text-[var(--color-foreground)]">{review.author}</span>
                          <span className="text-xs text-[var(--color-muted-foreground)]">{review.created_at}</span>
                        </div>
                        <RatingStars rating={review.rating} />
                        {review.verified_purchase && (
                          <span className="w-fit rounded-full bg-[var(--color-success-soft)] px-2 py-0.5 text-xs font-bold text-[var(--color-success)]">
                            已購買
                          </span>
                        )}
                        <p className="text-sm text-[var(--color-foreground)]">{review.comment}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  goBack();
                  setComparingGroupId(null);
                }}
                className="min-h-[44px] flex-1 rounded-2xl border-2 border-brand px-6 py-4 text-base font-bold text-brand"
              >
                返回選品類
              </button>
              <button
                type="button"
                onClick={goNext}
                disabled={cart.length === 0}
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
              >
                前往購物車（{cart.length}）
              </button>
            </div>
          </section>
        )}

        {/* ====== Step 3: Cart ====== */}
        {step === "cart" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">購物車</p>
            <div className="flex flex-col gap-4">
              {cartGroups.map((group) => (
                <div key={group.storeName} className="flex flex-col gap-2">
                  <p className="text-sm font-bold text-[var(--color-muted-foreground)]">{group.storeName}</p>
                  {group.lines.map((line) => (
                    <div
                      key={line.sku_id}
                      className="flex items-center justify-between rounded-xl border border-[var(--color-border)] px-4 py-3"
                    >
                      <div>
                        <p className="text-sm text-[var(--color-muted-foreground)]">
                          {line.productName}（{line.attributesLabel || "單一規格"}）
                        </p>
                        <p className="text-sm text-[var(--color-muted-foreground)]">NT${line.unitPrice * line.quantity}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => updateCartQuantity(line.sku_id, line.quantity - 1)}
                          className="flex h-8 w-8 items-center justify-center rounded-full border border-[var(--color-border)] text-[var(--color-muted-foreground)]"
                          aria-label="減少數量"
                        >
                          −
                        </button>
                        <span className="w-6 text-center text-base font-bold">{line.quantity}</span>
                        <button
                          type="button"
                          onClick={() => updateCartQuantity(line.sku_id, line.quantity + 1)}
                          className="flex h-8 w-8 items-center justify-center rounded-full bg-brand text-[var(--color-on-primary)]"
                          aria-label="增加數量"
                        >
                          +
                        </button>
                        <button
                          type="button"
                          onClick={() => removeFromCart(line.sku_id)}
                          className="ml-1 text-xs text-[var(--color-muted-foreground)] underline"
                          aria-label="移除"
                        >
                          移除
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>
            <div className="rounded-xl bg-[var(--color-canvas)] p-4">
              <div className="flex justify-between border-t border-[var(--color-border)] pt-2 text-base font-bold text-[var(--color-foreground)]">
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
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
              >
                前往結帳
              </button>
            </div>
          </section>
        )}

        {/* ====== Step 4: Checkout ====== */}
        {step === "checkout" && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">結帳</p>
            <div className="flex flex-col gap-3">
              <label className="flex flex-col gap-1">
                <span className="text-sm text-[var(--color-muted-foreground)]">聯絡人姓名</span>
                <input
                  value={contactName}
                  onChange={(e) => setContactName(e.target.value)}
                  className="rounded-xl border border-[var(--color-border)] px-4 py-3 text-base"
                />
              </label>
              <label className="flex flex-col gap-1">
                <span className="text-sm text-[var(--color-muted-foreground)]">聯絡電話</span>
                <input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="09XXXXXXXX"
                  className="rounded-xl border border-[var(--color-border)] px-4 py-3 text-base"
                />
              </label>
              {hasPhysicalItem && (
                <>
                  <label className="flex flex-col gap-1">
                    <span className="text-sm text-[var(--color-muted-foreground)]">收件城市</span>
                    <input
                      value={address.city}
                      onChange={(e) => setAddress((a) => ({ ...a, city: e.target.value }))}
                      className="rounded-xl border border-[var(--color-border)] px-4 py-3 text-base"
                    />
                  </label>
                  <label className="flex flex-col gap-1">
                    <span className="text-sm text-[var(--color-muted-foreground)]">收件地址</span>
                    <input
                      value={address.street}
                      onChange={(e) => setAddress((a) => ({ ...a, street: e.target.value }))}
                      className="rounded-xl border border-[var(--color-border)] px-4 py-3 text-base"
                    />
                  </label>
                </>
              )}
            </div>

            <div className="flex flex-col gap-3 rounded-xl border border-[var(--color-border)] p-4">
              <p className="text-sm text-[var(--color-muted-foreground)]">
                可用點數：{pointsBalance}（最多可折抵 {maxUsablePoints} 點）
              </p>
              <label className="flex flex-col gap-1">
                <span className="text-sm text-[var(--color-muted-foreground)]">使用點數折抵</span>
                <input
                  type="number"
                  min={0}
                  max={maxUsablePoints}
                  value={usedPoints}
                  onChange={(e) => setUsedPoints(Math.max(0, Math.min(maxUsablePoints, Number(e.target.value) || 0)))}
                  className="rounded-xl border border-[var(--color-border)] px-4 py-3 text-base"
                />
              </label>
            </div>

            {/*
              最終確認摘要卡（應付金額）套 GlassPanel 作為流程終點強調（Requirement 13.6、15.1）；
              其餘步驟卡維持不透明實色（Requirement 15.2）。
            */}
            <GlassPanel className="rounded-xl p-4">
              <div className="flex justify-between text-sm text-[var(--color-muted-foreground)]">
                <span>商品金額</span>
                <span>NT${cartTotal}</span>
              </div>
              <div className="flex justify-between text-sm text-[var(--color-muted-foreground)]">
                <span>運費</span>
                <span>NT${shippingFee}</span>
              </div>
              <div className="flex justify-between text-sm text-[var(--color-muted-foreground)]">
                <span>點數折抵</span>
                <span>-NT${Math.min(usedPoints, maxUsablePoints)}</span>
              </div>
              <div className="mt-1 flex justify-between border-t border-[var(--color-border)] pt-2 text-base font-bold text-[var(--color-foreground)]">
                <span>應付金額</span>
                <span>NT${orderTotal}</span>
              </div>
            </GlassPanel>

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
                className="min-h-[44px] flex-1 rounded-2xl bg-brand px-6 py-4 text-base font-bold text-[var(--color-on-primary)] disabled:opacity-40"
              >
                {submitting ? "送出中…" : "確認送出"}
              </button>
            </div>
          </section>
        )}

        {/* ====== Step 5: Result ====== */}
        {step === "result" && result && (
          <section className="flex flex-col gap-4">
            <p className="text-base font-bold leading-relaxed text-[var(--color-foreground)]">訂單完成</p>

            <div className="rounded-xl border border-brand/30 bg-brand/5 p-4">
              <p className="text-sm text-[var(--color-muted-foreground)]">訂單編號：{result.request_id}</p>
              <p className="text-sm text-[var(--color-muted-foreground)]">應付金額：NT${result.total_amount}</p>
              <p className="text-sm font-semibold text-brand">本次獲得點數：{result.points_earned}</p>
            </div>

            {Object.entries(result.redemption_codes).length > 0 && (
              <div className="flex flex-col gap-2 rounded-xl border border-[var(--color-border)] p-4">
                <p className="text-sm font-bold text-[var(--color-foreground)]">兌換碼</p>
                {Object.entries(result.redemption_codes).map(([skuId, codes]) => (
                  <div key={skuId} className="flex flex-col gap-1">
                    <span className="text-sm text-[var(--color-muted-foreground)]">{skuId}</span>
                    <div className="flex flex-wrap gap-2">
                      {codes.map((code) => (
                        <code key={code} className="rounded-lg bg-[var(--color-canvas)] px-3 py-2 font-mono text-sm">
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
                <div className="rounded-xl bg-[var(--color-canvas)] p-4">
                  <p className="text-sm text-[var(--color-muted-foreground)]">目前狀態：{order.status}</p>
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
