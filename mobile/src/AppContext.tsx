/**
 * AppContext.tsx — Theme, and who is signed in.
 *
 * On every launch the saved login token is sent to the backend
 * (POST /api/auth/refresh). The backend verifies it and returns the user's
 * details plus a fresh token; if the token is invalid or expired the app
 * goes back to the sign-in screen. If the phone is simply offline, the last
 * known user stays signed in so the app remains usable.
 */

import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { Colors, ThemeMode, darkColors, lightColors } from "./theme";
import { User } from "./types";
import * as api from "./api";
import * as authStorage from "./authStorage";

const THEME_KEY = "@budget_theme";

export type AuthStatus = "checking" | "signedOut" | "signedIn";

interface AppState {
  ready: boolean;
  mode: ThemeMode;
  colors: Colors;
  setMode: (m: ThemeMode) => void;
  authStatus: AuthStatus;
  user: User | null;
  /** Called by the sign-in / sign-up screen once the server accepted the credentials. */
  startSession: (token: string, user: User) => Promise<void>;
  signOut: () => Promise<void>;
  /** Debts still waiting to be returned in the active book (drives the header badge). */
  pendingDebts: number;
  setPendingDebts: (n: number) => void;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [mode, setModeState] = useState<ThemeMode>("dark");
  const [authStatus, setAuthStatus] = useState<AuthStatus>("checking");
  const [user, setUser] = useState<User | null>(null);
  const [pendingDebts, setPendingDebts] = useState(0);

  const startSession = useCallback(async (token: string, u: User) => {
    api.setAuthToken(token);
    await authStorage.saveToken(token);
    await authStorage.saveCachedUser(u);
    setUser(u);
    setAuthStatus("signedIn");
  }, []);

  const signOut = useCallback(async () => {
    api.setAuthToken(null);
    await authStorage.clearSession();
    // queued offline entries belong to the account that made them
    await api.clearPendingQueue().catch(() => {});
    setUser(null);
    setPendingDebts(0);
    setAuthStatus("signedOut");
  }, []);

  // Theme
  useEffect(() => {
    AsyncStorage.getItem(THEME_KEY)
      .then((stored) => {
        if (stored === "light" || stored === "dark") setModeState(stored);
      })
      .finally(() => setReady(true));
  }, []);

  // If the server ever rejects our token, drop back to the sign-in screen.
  useEffect(() => {
    api.setUnauthorizedHandler(() => {
      signOut();
    });
    return () => api.setUnauthorizedHandler(null);
  }, [signOut]);

  // Every time the app opens: verify the saved token with the backend.
  useEffect(() => {
    (async () => {
      const token = await authStorage.loadToken();
      if (!token) {
        setAuthStatus("signedOut");
        return;
      }
      api.setAuthToken(token);
      try {
        const res = await api.refreshSession();
        await startSession(res.token, res.user);
      } catch (err: any) {
        if (err instanceof api.ApiError && err.status === 401) {
          await signOut();
          return;
        }
        // Couldn't reach the server (offline): keep the last known user.
        const cached = await authStorage.loadCachedUser();
        if (cached) {
          setUser(cached);
          setAuthStatus("signedIn");
        } else {
          await signOut();
        }
      }
    })();
  }, []);

  const setMode = useCallback((m: ThemeMode) => {
    setModeState(m);
    AsyncStorage.setItem(THEME_KEY, m).catch(() => {});
  }, []);

  const value = useMemo<AppState>(
    () => ({
      ready,
      mode,
      colors: mode === "dark" ? darkColors : lightColors,
      setMode,
      authStatus,
      user,
      startSession,
      signOut,
      pendingDebts,
      setPendingDebts,
    }),
    [ready, mode, authStatus, user, setMode, startSession, signOut, pendingDebts]
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppState {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside <AppProvider>");
  return ctx;
}
