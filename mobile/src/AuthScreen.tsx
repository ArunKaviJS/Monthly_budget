/**
 * AuthScreen.tsx — Sign in / Sign up, shown after the opening screen
 * whenever nobody is signed in.
 */

import React, { useState } from "react";
import {
  ActivityIndicator,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useApp } from "./AppContext";
import * as api from "./api";
import { useKeyboardOverlap } from "./useKeyboardOverlap";

type Mode = "signin" | "signup";

const USERNAME_RE = /^[A-Za-z0-9_.]{3,24}$/;
const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/;

export default function AuthScreen() {
  const { colors: C, startSession } = useApp();
  const insets = useSafeAreaInsets();
  const { ref: kbRef, overlap, keyboardOpen } = useKeyboardOverlap();

  const [mode, setMode] = useState<Mode>("signin");
  const [identifier, setIdentifier] = useState("");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const switchMode = (m: Mode) => {
    setMode(m);
    setError("");
  };

  const validate = (): string => {
    if (mode === "signin") {
      if (!identifier.trim()) return "Enter your username or email";
      if (!password) return "Enter your password";
      return "";
    }
    if (!USERNAME_RE.test(username.trim()))
      return "Username must be 3–24 characters: letters, numbers, dot or underscore";
    if (!EMAIL_RE.test(email.trim())) return "Enter a valid email address";
    if (password.length < 6) return "Password must be at least 6 characters";
    return "";
  };

  const submit = async () => {
    if (busy) return;
    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res =
        mode === "signin"
          ? await api.signIn(identifier.trim(), password)
          : await api.signUp(username.trim(), email.trim(), password);
      await startSession(res.token, res.user);
    } catch (err: any) {
      if (err instanceof api.ApiError) setError(err.message);
      else setError("Can't reach the server. Check your internet connection and try again.");
    } finally {
      setBusy(false);
    }
  };

  const input = [
    styles.input,
    { backgroundColor: C.bgInput, color: C.textPrimary, borderColor: C.border },
  ];

  return (
    <View
      ref={kbRef}
      style={[styles.container, { backgroundColor: C.bg, paddingBottom: overlap }]}
    >
      <ScrollView
        contentContainerStyle={[
          styles.scroll,
          keyboardOpen && styles.scrollTyping,
          { paddingTop: insets.top + (keyboardOpen ? 12 : 24), paddingBottom: (overlap > 0 ? 0 : insets.bottom) + 24 },
        ]}
        keyboardShouldPersistTaps="handled"
      >
        {!keyboardOpen && <Text style={styles.emoji}>📒</Text>}
        <Text style={[styles.title, { color: C.textPrimary }, keyboardOpen && styles.titleTyping]}>
          {mode === "signin" ? "Welcome back" : "Create your account"}
        </Text>
        {!keyboardOpen && (
          <Text style={[styles.subtitle, { color: C.textSecondary }]}>
            {mode === "signin"
              ? "Sign in to see your budget books."
              : "Your books and expenses stay private to your account."}
          </Text>
        )}

        <View style={[styles.segment, { backgroundColor: C.bgCard, borderColor: C.border }]}>
          {(["signin", "signup"] as const).map((m) => (
            <TouchableOpacity
              key={m}
              style={[styles.segmentBtn, mode === m && { backgroundColor: C.accent }]}
              onPress={() => switchMode(m)}
            >
              <Text style={[styles.segmentText, { color: mode === m ? "#FFFFFF" : C.textMuted }]}>
                {m === "signin" ? "Sign in" : "Sign up"}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {mode === "signin" ? (
          <TextInput
            style={input}
            value={identifier}
            onChangeText={setIdentifier}
            placeholder="Username or email"
            placeholderTextColor={C.textMuted}
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="username"
            textContentType="username"
          />
        ) : (
          <>
            <TextInput
              style={input}
              value={username}
              onChangeText={setUsername}
              placeholder="Username"
              placeholderTextColor={C.textMuted}
              autoCapitalize="none"
              autoCorrect={false}
              autoComplete="username-new"
              textContentType="username"
              maxLength={24}
            />
            <TextInput
              style={input}
              value={email}
              onChangeText={setEmail}
              placeholder="Email"
              placeholderTextColor={C.textMuted}
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="email-address"
              autoComplete="email"
              textContentType="emailAddress"
            />
          </>
        )}

        <View style={styles.passwordRow}>
          <TextInput
            style={[...input, styles.passwordInput]}
            value={password}
            onChangeText={setPassword}
            placeholder={mode === "signup" ? "Password (6+ characters)" : "Password"}
            placeholderTextColor={C.textMuted}
            secureTextEntry={!showPassword}
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete={mode === "signup" ? "new-password" : "current-password"}
            textContentType={mode === "signup" ? "newPassword" : "password"}
            onSubmitEditing={submit}
          />
          <TouchableOpacity style={styles.showBtn} onPress={() => setShowPassword((v) => !v)}>
            <Text style={[styles.showText, { color: C.accent }]}>{showPassword ? "Hide" : "Show"}</Text>
          </TouchableOpacity>
        </View>

        {!!error && (
          <View style={[styles.errorBox, { backgroundColor: C.dangerBg, borderColor: C.error }]}>
            <Text style={[styles.errorText, { color: C.error }]}>{error}</Text>
          </View>
        )}

        <TouchableOpacity
          style={[styles.submit, { backgroundColor: C.accent }, busy && styles.busy]}
          onPress={submit}
          disabled={busy}
          activeOpacity={0.8}
        >
          {busy ? (
            <ActivityIndicator color="#FFFFFF" />
          ) : (
            <Text style={styles.submitText}>{mode === "signin" ? "Sign in" : "Create account"}</Text>
          )}
        </TouchableOpacity>

        <TouchableOpacity style={styles.switchRow} onPress={() => switchMode(mode === "signin" ? "signup" : "signin")}>
          <Text style={[styles.switchText, { color: C.textSecondary }]}>
            {mode === "signin" ? "New here? " : "Already have an account? "}
            <Text style={{ color: C.accent, fontWeight: "700" }}>
              {mode === "signin" ? "Create an account" : "Sign in"}
            </Text>
          </Text>
        </TouchableOpacity>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { ...StyleSheet.absoluteFill, zIndex: 900 },
  scroll: { flexGrow: 1, justifyContent: "center", paddingHorizontal: 24 },
  scrollTyping: { justifyContent: "flex-start" },
  titleTyping: { marginBottom: 16 },
  emoji: { fontSize: 46, textAlign: "center", marginBottom: 8 },
  title: { fontSize: 26, fontWeight: "800", textAlign: "center" },
  subtitle: { fontSize: 14, textAlign: "center", marginTop: 6, marginBottom: 22 },
  segment: {
    flexDirection: "row",
    borderRadius: 12,
    borderWidth: 1,
    padding: 4,
    marginBottom: 18,
  },
  segmentBtn: { flex: 1, paddingVertical: 10, borderRadius: 9, alignItems: "center" },
  segmentText: { fontSize: 14, fontWeight: "700" },
  input: {
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
    marginBottom: 12,
  },
  passwordRow: { justifyContent: "center" },
  passwordInput: { paddingRight: 64 },
  showBtn: { position: "absolute", right: 14, top: 0, bottom: 12, justifyContent: "center" },
  showText: { fontSize: 13, fontWeight: "700" },
  errorBox: { borderWidth: 1, borderRadius: 10, padding: 12, marginBottom: 12 },
  errorText: { fontSize: 13, fontWeight: "600" },
  submit: { borderRadius: 12, paddingVertical: 15, alignItems: "center", marginTop: 4 },
  submitText: { color: "#FFFFFF", fontSize: 16, fontWeight: "700" },
  busy: { opacity: 0.7 },
  switchRow: { paddingVertical: 18, alignItems: "center" },
  switchText: { fontSize: 14 },
});
