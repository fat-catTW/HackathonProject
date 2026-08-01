export interface HealthProduct {
  id: string;
  name: string;
  category: string;
  price: number;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  sodium_mg: number;
  tags: string[];
  allergens: string[];
}

export interface HealthRecommendationItem {
  product_id: string;
  name: string;
  reason: string;
  match_tags: string[];
  source?: string;
}

export interface HealthRecommendationResult {
  success: boolean;
  query: string;
  recommendations: HealthRecommendationItem[];
  fallback_used: boolean;
}
