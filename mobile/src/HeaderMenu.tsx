/**
 * HeaderMenu.tsx — Small "⋮" button for the top-right corner of the header.
 * Switch Light / Dark theme, see who is signed in, and sign out.
 */

import React, { useState } from "react";
import { Modal, Pressable, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useApp } from "./AppContext";

export default function HeaderMenu() {
  const { colors: C, mode, setMode, user, signOut } = useApp();
  const insets = useSafeAreaInsets();
  const [open, setOpen] = useState(false);

  const choose = (m: "dark" | "light") => {
    setMode(m);
    setOpen(false);
  };

  const handleSignOut = async () => {
    setOpen(false);
    await signOut();
  };

  return (
    <>
      <TouchableOpacity
        onPress={() => setOpen(true)}
        style={styles.button}
        hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        accessibilityLabel="Menu"
      >
        <Text style={[styles.dots, { color: C.textPrimary }]}>⋮</Text>
      </TouchableOpacity>

      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <View
            style={[
              styles.menu,
              { backgroundColor: C.bgCard, borderColor: C.border, top: insets.top + 48 },
            ]}
          >
            {user && (
              <>
                <View style={styles.account}>
                  <Text style={[styles.menuLabel, { color: C.textMuted, paddingHorizontal: 0 }]}>SIGNED IN AS</Text>
                  <Text style={[styles.accountName, { color: C.textPrimary }]} numberOfLines={1}>
                    {user.username}
                  </Text>
                  <Text style={[styles.accountEmail, { color: C.textSecondary }]} numberOfLines={1}>
                    {user.email}
                  </Text>
                </View>
                <View style={[styles.divider, { backgroundColor: C.border }]} />
              </>
            )}

            <Text style={[styles.menuLabel, { color: C.textMuted }]}>THEME</Text>
            <TouchableOpacity style={styles.item} onPress={() => choose("dark")}>
              <Text style={[styles.itemText, { color: C.textPrimary }]}>🌙  Dark</Text>
              {mode === "dark" && <Text style={[styles.check, { color: C.accent }]}>✓</Text>}
            </TouchableOpacity>
            <TouchableOpacity style={styles.item} onPress={() => choose("light")}>
              <Text style={[styles.itemText, { color: C.textPrimary }]}>☀️  Light</Text>
              {mode === "light" && <Text style={[styles.check, { color: C.accent }]}>✓</Text>}
            </TouchableOpacity>

            <View style={[styles.divider, { backgroundColor: C.border }]} />
            <TouchableOpacity style={styles.item} onPress={handleSignOut}>
              <Text style={[styles.itemText, { color: C.error }]}>🚪  Sign out</Text>
            </TouchableOpacity>
          </View>
        </Pressable>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  button: { paddingHorizontal: 16, paddingVertical: 4 },
  dots: { fontSize: 26, fontWeight: "900", lineHeight: 28 },
  backdrop: { flex: 1 },
  menu: {
    position: "absolute",
    right: 12,
    minWidth: 220,
    maxWidth: 280,
    borderRadius: 14,
    borderWidth: 1,
    paddingVertical: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 10,
    elevation: 10,
  },
  account: { paddingHorizontal: 16, paddingTop: 4, paddingBottom: 8 },
  accountName: { fontSize: 16, fontWeight: "800", marginTop: 2 },
  accountEmail: { fontSize: 12, marginTop: 2 },
  menuLabel: { fontSize: 11, fontWeight: "700", letterSpacing: 1, paddingHorizontal: 16, paddingVertical: 6 },
  item: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  itemText: { fontSize: 15, fontWeight: "600" },
  check: { fontSize: 16, fontWeight: "800" },
  divider: { height: 1, marginVertical: 4 },
});
