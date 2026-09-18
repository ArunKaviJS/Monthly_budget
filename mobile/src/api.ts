/**
 * api.ts — API client with offline queue support.
 *
 * All API calls go through this module.
 * When offline, POSTs are queued in AsyncStorage and flushed on reconnect.
 */

import AsyncStorage from "@react-native-async-storage/async-storage";
import {
  Expense,
  Book,
  PreviewResponse,
  MonthlySummary,
  DailySummaryResponse,
  IntentMeta,
  Budget,
  LearnedKeyword,
  PendingEntry,
  AuthResponse,
  Debt,
} from "./types";

// ── Base URL ──
// The backend address is fixed (not user-editable). For local development
// point the dev server at another backend with EXPO_PUBLIC_API_URL.
const DEFAULT_API_URL = "https://backend-ten-chi-67.vercel.app";

export async function getApiUrl(): Promise<string> {
  return (process.env.EXPO_PUBLIC_API_URL || DEFAULT_API_URL).replace(/\/+$/, "");
}

// ── Auth token ──
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

let _token: string | null = null;
let _onUnauthorized: (() => void) | null = null;

export function setAuthToken(token: string | null): void {
  _token = token;
}

/** Called when the server says the saved login is no longer valid. */
export function setUnauthorizedHandler(fn: (() => void) | null): void {
  _onUnauthorized = fn;
}

function extractDetail(status: number, body: string): string {
  try {
    const detail = JSON.parse(body)?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      const msg = String(detail[0]?.msg ?? "");
      return msg.replace(/^Value error, /, "") || "Please check what you entered";
    }
  } catch {}
  return body || `Request failed (${status})`;
}

// ── Connectivity ──
let _isOnline = true;
let _onlineListeners: Array<(online: boolean) => void> = [];

export function isOnline(): boolean {
  return _isOnline;
}

export function onConnectivityChange(cb: (online: boolean) => void): () => void {
  _onlineListeners.push(cb);
  return () => {
    _onlineListeners = _onlineListeners.filter((l) => l !== cb);
  };
}

function setOnline(online: boolean) {
  if (_isOnline !== online) {
    _isOnline = online;
    _onlineListeners.forEach((cb) => cb(online));
  }
}

// ── Generic fetch wrapper ──
const PUBLIC_PATHS = ["/api/auth/login", "/api/auth/signup", "/api/intents", "/api/health"];

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const isPublic = PUBLIC_PATHS.some((p) => path.startsWith(p));
  if (!_token && !isPublic) {
    throw new ApiError(401, "Not signed in");
  }

  const base = await getApiUrl();
  const url = `${base}${path}`;

  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(_token ? { Authorization: `Bearer ${_token}` } : {}),
        ...(options.headers || {}),
      },
    });

    setOnline(true);

    if (!res.ok) {
      const body = await res.text();
      if (res.status === 401 && _token && !path.startsWith("/api/auth/login")) {
        _onUnauthorized?.();
      }
      throw new ApiError(res.status, extractDetail(res.status, body));
    }

    // 204 No Content
    if (res.status === 204) return undefined as unknown as T;

    return (await res.json()) as T;
  } catch (err: any) {
    if (
      !(err instanceof ApiError) &&
      (err.message?.includes("Network request failed") ||
        err.message?.includes("Failed to fetch") ||
        err.message?.includes("TypeError"))
    ) {
      setOnline(false);
    }
    throw err;
  }
}

// ── Offline Queue ──
const QUEUE_KEY = "@budget_pending_queue";

export async function getPendingQueue(): Promise<PendingEntry[]> {
  const raw = await AsyncStorage.getItem(QUEUE_KEY);
  return raw ? JSON.parse(raw) : [];
}

export async function clearPendingQueue(): Promise<void> {
  await AsyncStorage.removeItem(QUEUE_KEY);
}

async function addToQueue(rawText: string, intent: string): Promise<void> {
  const queue = await getPendingQueue();
  queue.push({
    id: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    raw_text: rawText,
    intent,
    timestamp: Date.now(),
  });
  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}

async function removeFromQueue(id: string): Promise<void> {
  const queue = await getPendingQueue();
  const filtered = queue.filter((e) => e.id !== id);
  await AsyncStorage.setItem(QUEUE_KEY, JSON.stringify(filtered));
}

export async function flushQueue(): Promise<number> {
  const queue = await getPendingQueue();
  let flushed = 0;

  for (const entry of queue) {
    try {
      await apiFetch<Expense>("/api/expenses", {
        method: "POST",
        body: JSON.stringify({ raw_text: entry.raw_text, intent: entry.intent }),
      });
      await removeFromQueue(entry.id);
      flushed++;
    } catch {
      // Still offline, stop flushing
      break;
    }
  }

  return flushed;
}

// ── API Methods ──

// Auth
export async function signUp(username: string, email: string, password: string): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });
}

export async function signIn(identifier: string, password: string): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ identifier, password }),
  });
}

/** Asks the server to verify the saved token; returns the user + a fresh token. */
export async function refreshSession(): Promise<AuthResponse> {
  return apiFetch<AuthResponse>("/api/auth/refresh", { method: "POST" });
}

// Books
export async function getBooks(): Promise<Book[]> {
  return apiFetch<Book[]>("/api/books");
}

export async function getActiveBook(): Promise<Book | null> {
  try {
    return await apiFetch<Book>("/api/books/active");
  } catch {
    return null;
  }
}

export async function createBook(name: string): Promise<Book> {
  return apiFetch<Book>("/api/books", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export async function renameBook(id: number, name: string): Promise<Book> {
  return apiFetch<Book>(`/api/books/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ name }),
  });
}

export async function setActiveBook(id: number): Promise<Book> {
  return apiFetch<Book>(`/api/books/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ is_active: true }),
  });
}

export async function deleteBook(id: number): Promise<number> {
  const res = await apiFetch<{ deleted_expenses: number }>(`/api/books/${id}`, {
    method: "DELETE",
  });
  return res.deleted_expenses;
}

// Debts (money given to / got from other people, kept inside a book)
export async function getDebts(bookId?: number, status?: "pending" | "settled"): Promise<Debt[]> {
  const params = new URLSearchParams();
  if (bookId != null) params.set("book_id", String(bookId));
  if (status) params.set("status", status);
  const qs = params.toString();
  return apiFetch<Debt[]>(`/api/debts${qs ? `?${qs}` : ""}`);
}

export async function createDebt(data: {
  person: string;
  amount: number;
  direction: "lent" | "borrowed";
  reason?: string;
  date?: string;
}): Promise<Debt> {
  return apiFetch<Debt>("/api/debts", { method: "POST", body: JSON.stringify(data) });
}

export async function updateDebt(
  id: number,
  data: {
    person?: string;
    amount?: number;
    direction?: "lent" | "borrowed";
    reason?: string;
    date?: string;
    status?: "pending" | "settled";
    settled_on?: string;
  }
): Promise<Debt> {
  return apiFetch<Debt>(`/api/debts/${id}`, { method: "PATCH", body: JSON.stringify(data) });
}

export async function deleteDebt(id: number): Promise<void> {
  return apiFetch<void>(`/api/debts/${id}`, { method: "DELETE" });
}

// Expenses
export async function createExpense(rawText: string, intent: string): Promise<Expense | null> {
  try {
    const result = await apiFetch<Expense>("/api/expenses", {
      method: "POST",
      body: JSON.stringify({ raw_text: rawText, intent }),
    });

    // Try to flush any pending entries too
    flushQueue().catch(() => {});

    return result;
  } catch (err: any) {
    // Only queue when we're actually offline / can't reach the server.
    // A real API error (e.g. 422 "no amount found") must surface to the
    // user instead of being silently swallowed into the pending queue.
    if (!isOnline()) {
      await addToQueue(rawText, intent);
      return null;
    }
    throw err;
  }
}

export async function getExpenses(
  month?: string,
  intent?: string,
  limit = 100,
  bookId?: number
): Promise<Expense[]> {
  const params = new URLSearchParams();
  if (month) params.set("month", month);
  if (intent) params.set("intent", intent);
  if (bookId != null) params.set("book_id", String(bookId));
  params.set("limit", String(limit));

  return apiFetch<Expense[]>(`/api/expenses?${params.toString()}`);
}

export async function updateExpense(
  id: number,
  data: { amount?: number; intent?: string; description?: string; date?: string }
): Promise<Expense> {
  return apiFetch<Expense>(`/api/expenses/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteExpense(id: number): Promise<void> {
  return apiFetch<void>(`/api/expenses/${id}`, { method: "DELETE" });
}

export async function deleteAllExpenses(): Promise<number> {
  const res = await apiFetch<{ deleted: number }>("/api/expenses", {
    method: "DELETE",
  });
  return res.deleted;
}

// Preview
export async function previewExpense(rawText: string): Promise<PreviewResponse> {
  return apiFetch<PreviewResponse>("/api/preview", {
    method: "POST",
    body: JSON.stringify({ raw_text: rawText }),
  });
}

// Summary
export async function getMonthlySummary(month?: string, bookId?: number): Promise<MonthlySummary> {
  const params = new URLSearchParams();
  if (bookId != null) params.set("book_id", String(bookId));
  else if (month) params.set("month", month);
  const qs = params.toString();
  return apiFetch<MonthlySummary>(`/api/summary${qs ? `?${qs}` : ""}`);
}

export async function getDailySummary(month?: string): Promise<DailySummaryResponse> {
  const params = month ? `?month=${month}` : "";
  return apiFetch<DailySummaryResponse>(`/api/summary/daily${params}`);
}

// Intents
export async function getIntents(): Promise<IntentMeta[]> {
  return apiFetch<IntentMeta[]>("/api/intents");
}

// Budgets
export async function getBudgets(): Promise<Budget[]> {
  return apiFetch<Budget[]>("/api/budgets");
}

export async function setBudget(intent: string, monthlyLimit: number): Promise<Budget> {
  return apiFetch<Budget>("/api/budgets", {
    method: "POST",
    body: JSON.stringify({ intent, monthly_limit: monthlyLimit }),
  });
}

// Keywords
export async function getKeywords(): Promise<LearnedKeyword[]> {
  return apiFetch<LearnedKeyword[]>("/api/keywords");
}

export async function deleteKeyword(keyword: string): Promise<void> {
  return apiFetch<void>(`/api/keywords/${encodeURIComponent(keyword)}`, {
    method: "DELETE",
  });
}

export async function clearKeywords(): Promise<void> {
  return apiFetch<void>("/api/keywords", { method: "DELETE" });
}

// Export
export async function exportData(
  format: "json" | "csv",
  month?: string
): Promise<string> {
  const base = await getApiUrl();
  const params = month ? `?month=${month}` : "";
  const res = await fetch(`${base}/api/export/${format}${params}`, {
    headers: _token ? { Authorization: `Bearer ${_token}` } : {},
  });
  const text = await res.text();
  if (!res.ok) throw new ApiError(res.status, extractDetail(res.status, text));
  return text;
}

// Health
export async function checkHealth(): Promise<boolean> {
  try {
    await apiFetch("/api/health");
    return true;
  } catch {
    return false;
  }
}
