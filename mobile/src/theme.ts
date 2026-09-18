/**
 * theme.ts — Design tokens for the app.
 */

export type ThemeMode = "dark" | "light";

export interface Colors {
  bg: string;
  bgCard: string;
  bgInput: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  accent: string;
  success: string;
  warning: string;
  error: string;
  border: string;
  overlay: string;
  dangerBg: string;
  offlineBg: string;
  offlineBorder: string;
}

export const darkColors: Colors = {
  bg: "#0F172A",
  bgCard: "#1E293B",
  bgInput: "#334155",
  textPrimary: "#F8FAFC",
  textSecondary: "#94A3B8",
  textMuted: "#64748B",
  accent: "#38BDF8",
  success: "#10B981",
  warning: "#F59E0B",
  error: "#EF4444",
  border: "#334155",
  overlay: "rgba(0, 0, 0, 0.6)",
  dangerBg: "rgba(239, 68, 68, 0.12)",
  offlineBg: "rgba(239, 68, 68, 0.15)",
  offlineBorder: "rgba(239, 68, 68, 0.3)",
};

export const lightColors: Colors = {
  bg: "#F1F5F9",
  bgCard: "#FFFFFF",
  bgInput: "#E2E8F0",
  textPrimary: "#0F172A",
  textSecondary: "#475569",
  textMuted: "#64748B",
  accent: "#0284C7",
  success: "#059669",
  warning: "#D97706",
  error: "#DC2626",
  border: "#CBD5E1",
  overlay: "rgba(15, 23, 42, 0.45)",
  dangerBg: "rgba(220, 38, 38, 0.08)",
  offlineBg: "rgba(220, 38, 38, 0.08)",
  offlineBorder: "rgba(220, 38, 38, 0.25)",
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
};

export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  full: 9999,
};

export const fonts = {
  size: {
    xs: 11,
    sm: 13,
    md: 15,
    lg: 18,
    xl: 22,
    xxl: 28,
    hero: 36,
  },
  weight: {
    normal: "400" as const,
    medium: "500" as const,
    semibold: "600" as const,
    bold: "700" as const,
    heavy: "800" as const,
  },
};
