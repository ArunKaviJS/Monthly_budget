/**
 * authStorage.ts — Remembers who is signed in across app restarts.
 *
 * The login token goes into the phone's secure storage (Keychain / Keystore).
 * On web, where that doesn't exist, it falls back to normal storage.
 */

import { Platform } from "react-native";
import * as SecureStore from "expo-secure-store";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { User } from "./types";

const TOKEN_KEY = "budget_auth_token";
const USER_KEY = "@budget_user";
const useSecureStore = Platform.OS !== "web";

export async function loadToken(): Promise<string | null> {
  try {
    return useSecureStore
      ? await SecureStore.getItemAsync(TOKEN_KEY)
      : await AsyncStorage.getItem("@" + TOKEN_KEY);
  } catch {
    return null;
  }
}

export async function saveToken(token: string): Promise<void> {
  if (useSecureStore) await SecureStore.setItemAsync(TOKEN_KEY, token);
  else await AsyncStorage.setItem("@" + TOKEN_KEY, token);
}

export async function loadCachedUser(): Promise<User | null> {
  try {
    const raw = await AsyncStorage.getItem(USER_KEY);
    return raw ? (JSON.parse(raw) as User) : null;
  } catch {
    return null;
  }
}

export async function saveCachedUser(user: User): Promise<void> {
  await AsyncStorage.setItem(USER_KEY, JSON.stringify(user));
}

export async function clearSession(): Promise<void> {
  try {
    if (useSecureStore) await SecureStore.deleteItemAsync(TOKEN_KEY);
    else await AsyncStorage.removeItem("@" + TOKEN_KEY);
  } catch {}
  await AsyncStorage.removeItem(USER_KEY).catch(() => {});
}
