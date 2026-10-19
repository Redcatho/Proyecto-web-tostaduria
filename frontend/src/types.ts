export type User = {
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
  is_active: boolean;
  roles: string[];
};

export type Business = {
  id: number;
  legal_name: string | null;
  tax_id: string | null;
  business_type: "cafeteria" | "supermarket" | "wholesaler" | null;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  profile_status: "incomplete" | "complete";
  is_active: boolean;
  addresses: Address[];
};

export type Address = {
  id: number;
  label: string;
  line1: string;
  city: string;
  state: string;
  is_primary: boolean;
};

export type CreditApplication = {
  id: number;
  requested_days: number;
  requested_limit_usd: string;
  justification: string | null;
  status: string;
  review_note: string | null;
  created_at: string;
  business_id?: number;
  business_name?: string | null;
};

export type CreditTerms = {
  id: number;
  payment_days: number;
  credit_limit_usd: string;
  is_active: boolean;
  note: string | null;
};

export type CatalogVariant = {
  id: number;
  sku: string;
  name: string;
  quality_code: string | null;
  sale_unit: string;
  inventory_unit: string;
  unit_weight_kg: string;
  packages_per_unit: number | null;
  price_usd: string;
  price_ves: string | null;
  availability: string;
  stock?: string;
  low_stock_threshold?: string;
};

export type CatalogProduct = {
  id: number;
  slug: string;
  line: "commercial" | "cafeteria";
  name: string;
  description: string | null;
  coffee_type: string | null;
  variety: string | null;
  origin: string | null;
  sensory_notes: string | null;
  image_url: string | null;
  is_active: boolean;
  variants: CatalogVariant[];
};

export type ExchangeRate = { currency: string; rate_ves: string; effective_date: string; source: string; id?: number; source_method?: string; note?: string | null };

export type CartItem = { id: number; variant_id: number; product_name: string; variant_name: string; line: string; quantity: string; unit: string; roast_profile: string | null; customer_note: string | null; unit_price_usd: string; discount_per_unit_usd: string; line_total_usd: string; availability_stock: string };
export type CartSummary = { items: CartItem[]; cafe_total_kg: string; discount_per_kg: string; subtotal_usd: string; discount_usd: string; total_usd: string; total_ves: string | null; exchange_rate: { rate_ves: string; effective_date: string } | null; estimated_dispatch_hours?: number | null; estimate_note?: string };
export type PaymentSubmission = { id: number; currency: string; amount: string; amount_usd_equivalent: string; reference: string; payment_method: string; proof_original_filename: string; note?: string | null; status: string; review_note: string | null; submitted_at: string };
export type Order = { id: number; number: string; status: string; payment_condition: string | null; total_usd: string | null; total_ves: string | null; rate_ves: string | null; required_payment_usd: string; verified_payment_usd: string; outstanding_usd: string; created_at: string; production_started_at?: string | null; delivered_at?: string | null; estimated_dispatch_hours?: number | null; estimate_note?: string | null; dispatch_guide?: { carrier_name: string; tracking_number: string | null; dispatch_note: string | null; dispatched_at: string } | null; history?: { status: string; note: string | null; created_at: string }[]; payments?: PaymentSubmission[]; items: { id: number; sku: string; product_name: string; quantity: string; roast_profile: string | null; line_total_usd: string }[] };
