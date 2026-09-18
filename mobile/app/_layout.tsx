/**
 * _layout.tsx — Root layout for expo-router.
 * Sets up the stack navigator, theme + account context, the opening
 * signature screen, and the sign-in / sign-up gate.
 */

import React, { useState } from "react";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { AppProvider, useApp } from "../src/AppContext";
import SplashOverlay from "../src/SplashOverlay";
import AuthScreen from "../src/AuthScreen";

function RootStack() {
  const { colors: C, mode, authStatus, user } = useApp();
  const [splashDone, setSplashDone] = useState(false);

  return (
    <View style={[styles.container, { backgroundColor: C.bg }]}>
      <StatusBar style={mode === "dark" ? "light" : "dark"} />

      {/* Re-created whenever a different person signs in, so no screen keeps
          the previous account's data. */}
      <Stack
        key={user?.id ?? "guest"}
        screenOptions={{
          headerStyle: { backgroundColor: C.bg },
          headerTintColor: C.textPrimary,
          headerTitleStyle: { fontWeight: "700" },
          contentStyle: { backgroundColor: C.bg },
          headerShadowVisible: false,
        }}
      >
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen name="debts" options={{ title: "Debts", presentation: "card" }} />
        <Stack.Screen
          name="detail/[intent]"
          options={{
            title: "Category Detail",
            presentation: "card",
          }}
        />
      </Stack>

      {splashDone && authStatus === "checking" && (
        <View style={[styles.checking, { backgroundColor: C.bg }]}>
          <ActivityIndicator color={C.accent} size="large" />
          <Text style={[styles.checkingText, { color: C.textSecondary }]}>Signing you in…</Text>
        </View>
      )}
      {splashDone && authStatus === "signedOut" && <AuthScreen />}
      {!splashDone && <SplashOverlay onDone={() => setSplashDone(true)} />}
    </View>
  );
}

export default function RootLayout() {
  return (
    <AppProvider>
      <RootStack />
    </AppProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  checking: {
    ...StyleSheet.absoluteFill,
    alignItems: "center",
    justifyContent: "center",
    zIndex: 900,
  },
  checkingText: { marginTop: 14, fontSize: 14, fontWeight: "600" },
});
