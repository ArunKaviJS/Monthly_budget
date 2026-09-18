/**
 * helpers.ts — Formatting utilities for the app.
 */

/**
 * Format a number in Indian numbering system with ₹ prefix.
 * e.g., 123456 -> "₹1,23,456"
 */
export function formatINR(amount: number | string): string {
  const num = typeof amount === "string" ? parseFloat(amount) : amount;
  if (isNaN(num)) return "₹0";

  const isNegative = num < 0;
  const absNum = Math.abs(num);

  // Split into integer and decimal
  const parts = absNum.toFixed(2).split(".");
  let intPart = parts[0];
  const decPart = parts[1];

  // Indian formatting: first 3 from right, then groups of 2
  if (intPart.length > 3) {
    const last3 = intPart.slice(-3);
    const rest = intPart.slice(0, -3);
    const grouped = rest.replace(/\B(?=(\d{2})+(?!\d))/g, ",");
    intPart = grouped + "," + last3;
  }

  // Remove trailing .00
  const decimal = decPart === "00" ? "" : `.${decPart}`;
  const sign = isNegative ? "-" : "";

  return `${sign}₹${intPart}${decimal}`;
}

/**
 * Get the current month in YYYY-MM format (IST).
 */
export function getCurrentMonth(): string {
  const now = new Date();
  // Simple IST offset: +5:30
  const ist = new Date(now.getTime() + (5.5 * 60 * 60 * 1000));
  const y = ist.getUTCFullYear();
  const m = String(ist.getUTCMonth() + 1).padStart(2, "0");
  return `${y}-${m}`;
}

/**
 * Today's date as YYYY-MM-DD (IST).
 */
export function getToday(): string {
  const ist = new Date(Date.now() + 5.5 * 60 * 60 * 1000);
  return ist.toISOString().slice(0, 10);
}

/**
 * Format month string "YYYY-MM" to display name.
 */
export function formatMonth(month: string): string {
  const [y, m] = month.split("-");
  const names = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
  ];
  return `${names[parseInt(m, 10) - 1]} ${y}`;
}

/**
 * Navigate to previous/next month from "YYYY-MM".
 */
export function prevMonth(month: string): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m - 2, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function nextMonth(month: string): string {
  const [y, m] = month.split("-").map(Number);
  const d = new Date(y, m, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

/**
 * Format a date string "YYYY-MM-DD" to a short display.
 */
export function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  const day = d.getDate();
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${day} ${months[d.getMonth()]}`;
}

/**
 * Debounce helper.
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  ms: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
