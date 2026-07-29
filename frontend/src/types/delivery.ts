export interface DeliveryStore {
  id: string;
  name: string;
  address: string;
  cuisine: string;
  image: string | null;
}

export interface ModifierOption {
  label: string;
  price: number;
}

export interface ModifierGroup {
  name: string;
  options: ModifierOption[];
}

export interface MenuItem {
  id: string;
  title: string;
  price: number;
  modifier_group: ModifierGroup[];
}

export interface DeliveryStoreDetail extends DeliveryStore {
  url: string;
  menu: MenuItem[];
}

export interface DeliveryAddress {
  lat: number;
  lng: number;
  area: string;
  city: string;
  street: string;
  remark: string;
  contact_name: string;
  phone?: string;
}

export interface CartItem {
  id: string;
  title: string;
  quantity: number;
  price: number;
  modifier_group: { name: string; selected: string }[];
}

export interface DeliveryPayload {
  address: DeliveryAddress;
  goods: CartItem[];
  store_id: string;
  store_name: string;
  store_address: string;
  store_url?: string;
  note?: string;
  shipping_fee?: number;
}

export interface DeliverySubmitResult {
  success: boolean;
  request_id: string;
  order_status: string;
  total_amount: number;
}

export interface DeliveryDriverInfo {
  driver_name: string;
  driver_phone: string;
  eta_minutes: number;
}

export interface DeliveryOrder {
  request_id: string;
  status: string;
  order_status: string;
  order_status_label: string;
  order_items: {
    user: { address: DeliveryAddress };
    goods: CartItem[];
    store: { id: string; name: string; address: string; url: string };
    note: string;
  };
  original_amount: number;
  shipping_fee_amount: number;
  total_amount: number;
  vendor_data: {
    delivery: DeliveryDriverInfo | null;
    order_status: number | null;
  };
  cancel_reason: string | null;
  created_at: string;
}
