/**
 * DebtsButton.tsx — Header symbol that opens the Debts screen.
 * A small red notification badge shows how many debts in the active book
 * are still pending, and disappears once everything has been returned.
 */

import React from "react";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useRouter } from "expo-router";
import { useApp } from "./AppContext";

export default function DebtsButton() {
  const { colors: C, pendingDebts } = useApp();
  const router = useRouter();

  return (
    <TouchableOpacity
      onPress={() => router.push("/debts")}
      style={styles.button}
      hitSlop={{ top: 10, bottom: 10, left: 6, right: 6 }}
      accessibilityLabel={pendingDebts > 0 ? `Debts, ${pendingDebts} pending` : "Debts"}
    >
      <Text style={styles.icon}>🤝</Text>
      {pendingDebts > 0 && (
        <View style={[styles.badge, { backgroundColor: C.error, borderColor: C.bg }]}>
          <Text style={styles.badgeText}>{pendingDebts > 9 ? "9+" : pendingDebts}</Text>
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: { paddingHorizontal: 10, paddingVertical: 4 },
  icon: { fontSize: 22 },
  badge: {
    position: "absolute",
    top: -2,
    right: 2,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    borderWidth: 2,
    paddingHorizontal: 3,
    alignItems: "center",
    justifyContent: "center",
  },
  badgeText: { color: "#FFFFFF", fontSize: 10, fontWeight: "800", lineHeight: 12 },
});
