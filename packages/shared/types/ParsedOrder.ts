/**
 * ParsedOrder
 * Structured data extracted from a raw freelance order.
 * Mirror of backend app/schemas/order.py :: ParsedOrder
 */
export interface ParsedOrder {
  client_name: string | null;
  event_type: string | null;
  city: string | null;
  location: string | null;
  date: string | null;          // ISO date string "YYYY-MM-DD"
  duration: string | null;
  budget_max: number | null;
  requirements: string[];
}
