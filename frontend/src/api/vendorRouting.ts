import { actOnVendorRequest, getVendorRequest, listVendorRequests, revealVendorContact } from "./vendor";
import {
  actOnVendorDeliveryOrder,
  getVendorDeliveryOrder,
  listVendorDeliveryOrders,
  revealVendorDeliveryContact,
} from "./vendorDelivery";
import { actOnVendorShopOrder, getVendorShopOrder, listVendorShopOrders, revealVendorShopContact } from "./vendorShop";
import type { VendorKind } from "../types/vendor";

const API_BY_KIND = {
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
} as const;

export function getVendorApiForKind(kind: VendorKind) {
  return API_BY_KIND[kind];
}
