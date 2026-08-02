import { actOnVendorRequest, getVendorRequest, listVendorRequests, revealVendorContact } from "./vendor";
import {
  actOnVendorDeliveryOrder,
  getVendorDeliveryOrder,
  listVendorDeliveryOrders,
  revealVendorDeliveryContact,
} from "./vendorDelivery";
import { actOnVendorShopOrder, getVendorShopOrder, listVendorShopOrders, revealVendorShopContact } from "./vendorShop";
import type {
  VendorAction,
  VendorActionResult,
  VendorContactReveal,
  VendorKind,
  VendorRequestDetail,
  VendorRequestList,
  VendorScope,
} from "../types/vendor";

/**
 * 三種後台共用的介面，讓明細頁不必知道自己連的是哪一種。
 *
 * `act` 的 amount 只有一般服務的報價用得到；外送與商城的實作少收這個參數，TypeScript
 * 允許少收參數的函式塞進多參數的簽章，所以那兩邊不必為了型別去掛一個永遠不看的參數。
 */
interface VendorApiSet {
  list: (scope: VendorScope) => Promise<VendorRequestList>;
  get: (requestId: string) => Promise<VendorRequestDetail>;
  act: (
    requestId: string,
    action: VendorAction,
    version: number,
    amount?: number,
  ) => Promise<VendorActionResult>;
  reveal: (requestId: string) => Promise<VendorContactReveal>;
}

const API_BY_KIND: Record<VendorKind, VendorApiSet> = {
  generic: {
    list: listVendorRequests,
    get: getVendorRequest,
    act: actOnVendorRequest,
    reveal: revealVendorContact,
  },
  delivery: {
    list: listVendorDeliveryOrders,
    get: getVendorDeliveryOrder,
    act: actOnVendorDeliveryOrder,
    reveal: revealVendorDeliveryContact,
  },
  shop: {
    list: listVendorShopOrders,
    get: getVendorShopOrder,
    act: actOnVendorShopOrder,
    reveal: revealVendorShopContact,
  },
};

export function getVendorApiForKind(kind: VendorKind) {
  return API_BY_KIND[kind];
}
