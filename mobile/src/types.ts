/**
 * types.ts — TypeScript types matching the backend Pydantic schemas.
 */

export interface User {
  id: number;
  username: string;
  email: string;
}

export interface AuthResponse {
  token: string;
  user: User;
}

export interface Expense {
  id: number;
  book_id: number | null;
  raw_text: string;
  description: string;
  amount: number;
  intent: string;
  confidence: number | null;
  spent_on: string; // "YYYY-MM-DD"
  created_at: string | null;
  is_manual_override: boolean;
}

export interface Book {
  id: number;
  name: string;
  is_active: boolean;
  created_at: string | null;
  total: number;
  count: number;
  pending_debts: number;
}

export interface PreviewResponse {
  intent: string;
  confidence: number;
  description: string;
  amount: number | null;
  matched_keywords: string[];
  reason: string;
}

export interface IntentSummary {
  intent: string;
  label: string;
  emoji: string;
  colour: string;
  total: number;
  count: number;
  percent: number;
  budget_limit: number | null;
  remaining: number | null;
}

export interface MonthlySummary {
  month: string;
  total: number;
  count: number;
  budget_total: number | null;
  intents: IntentSummary[];
}

export interface DailySummary {
  date: string;
  total: number;
  count: number;
}

export interface DailySummaryResponse {
  month: string;
  days: DailySummary[];
}

export interface IntentMeta {
  intent: string;
  label: string;
  emoji: string;
  colour: string;
}

export interface Budget {
  intent: string;
  monthly_limit: number;
}

export interface LearnedKeyword {
  keyword: string;
  intent: string;
  hits: number;
}

export interface HealthResponse {
  status: string;
  database: string;
  version: string;
}

export interface PendingEntry {
  id: string; // local UUID
  raw_text: string;
  intent: string;
  timestamp: number;
}

export interface Debt {
  id: number;
  book_id: number;
  direction: "lent" | "borrowed"; // lent = I gave, borrowed = I got
  person: string;
  reason: string | null;
  amount: number;
  date: string; // when it was given / got
  status: "pending" | "settled";
  settled_on: string | null; // when it came back
  created_at: string | null;
}
