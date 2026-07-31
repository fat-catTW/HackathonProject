export interface ShopStore {
  id: string;
  name: string;
  category: string;
  image: string | null;
}

export interface ShopCategory {
  id: string;
  name: string;
}

export interface ShopSpec {
  name: string;
  options: string[];
}

export interface ShopSku {
  sku_id: string;
  attributes: Record<string, string>;
  unit_price: number;
  unit_points: number;
}

export interface ShopProduct {
  id: string;
  store_id: string;
  store_name: string;
  category_id: string;
  name: string;
  description: string;
  product_type: "PHYSICAL" | "SERIAL_CODE";
  image: string | null;
  specs: ShopSpec[];
  skus: ShopSku[];
}

export interface ShopCartLine {
  sku_id: string;
  quantity: number;
}

export interface ShopAddress {
  city: string;
  street: string;
  contact_name: string;
  remark?: string;
}

export interface ShopSubmitPayload {
  cart: ShopCartLine[];
  contact_name: string;
  phone: string;
  address?: ShopAddress;
  used_points: number;
}

export interface ShopSubmitResult {
  success: boolean;
  request_id: string;
  status: string;
  total_amount: number;
  points_earned: number;
  redemption_codes: Record<string, string[]>;
}

export interface ShopOrder {
  request_id: string;
  status: string;
  order_type: string;
  form_data: {
    cart: ShopCartLine[];
    contact_name: string;
    phone: string;
    address: ShopAddress | null;
    used_points: number;
  };
  original_amount: number;
  shipping_fee_amount: number;
  points_discount: number;
  total_amount: number;
  points_earned: number;
  redemption_codes: Record<string, string[]>;
  status_history: { status: string; at: string }[];
  cancel_reason: string | null;
  created_at: string;
}

export interface ShopPointsBalance {
  balance: number;
}
