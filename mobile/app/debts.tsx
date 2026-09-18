/**
 * debts.tsx — Debts screen.
 *
 * Money you gave to friends ("I gave": they owe you) and money you got from
 * others ("I got": you owe them), kept inside the active book. Each entry has
 * who, what for, and when. While pending it counts toward the badge on Home;
 * mark it returned and it moves to "Returned" and the badge count drops.
 * Debts are separate from expenses and never change their totals.
 */

import React, { useCallback, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  Modal,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { useFocusEffect } from "expo-router";
import * as api from "../src/api";
import { useApp } from "../src/AppContext";
import { Colors } from "../src/theme";
import { useKeyboardOverlap } from "../src/useKeyboardOverlap";
import { formatDate, formatINR, getToday } from "../src/helpers";
import { Book, Debt } from "../src/types";

type Direction = "lent" | "borrowed";
type Tab = "pending" | "settled";

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

export default function DebtsScreen() {
  const { colors: C, setPendingDebts } = useApp();
  const styles = useMemo(() => makeStyles(C), [C]);
  const { ref: kbRef, overlap } = useKeyboardOverlap();
  const modalKb = useKeyboardOverlap();

  const [book, setBook] = useState<Book | null>(null);
  const [debts, setDebts] = useState<Debt[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [tab, setTab] = useState<Tab>("pending");

  // Add form
  const [formOpen, setFormOpen] = useState(false);
  const [direction, setDirection] = useState<Direction>("lent");
  const [person, setPerson] = useState("");
  const [amount, setAmount] = useState("");
  const [reason, setReason] = useState("");
  const [date, setDate] = useState(getToday());
  const [formError, setFormError] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoadError("");
    try {
      const activeBook = await api.getActiveBook();
      setBook(activeBook);
      if (activeBook) {
        const rows = await api.getDebts(activeBook.id);
        setDebts(rows);
        setPendingDebts(rows.filter((d) => d.status === "pending").length);
      } else {
        setDebts([]);
        setPendingDebts(0);
      }
    } catch (err: any) {
      setLoadError(err?.message || "Couldn't load debts");
    } finally {
      setLoading(false);
    }
  }, [setPendingDebts]);

  useFocusEffect(
    useCallback(() => {
      load();
    }, [load])
  );

  const pending = debts.filter((d) => d.status === "pending");
  const settled = debts.filter((d) => d.status === "settled");
  const willGet = pending.filter((d) => d.direction === "lent").reduce((s, d) => s + Number(d.amount), 0);
  const owe = pending.filter((d) => d.direction === "borrowed").reduce((s, d) => s + Number(d.amount), 0);
  const shown = tab === "pending" ? pending : settled;

  // ── actions ──
  const openForm = () => {
    setDirection("lent");
    setPerson("");
    setAmount("");
    setReason("");
    setDate(getToday());
    setFormError("");
    setFormOpen(true);
  };

  const saveDebt = async () => {
    if (saving) return;
    const n = parseFloat(amount);
    if (!person.trim()) return setFormError("Enter the name of the person");
    if (isNaN(n) || n <= 0) return setFormError("Enter an amount greater than 0");
    if (!DATE_RE.test(date.trim())) return setFormError("Enter the date as YYYY-MM-DD");

    setSaving(true);
    setFormError("");
    try {
      await api.createDebt({
        person: person.trim(),
        amount: n,
        direction,
        reason: reason.trim() || undefined,
        date: date.trim(),
      });
      setFormOpen(false);
      setTab("pending");
      await load();
    } catch (err: any) {
      setFormError(err?.message || "Couldn't save. Try again.");
    } finally {
      setSaving(false);
    }
  };

  const setStatus = async (d: Debt, status: "pending" | "settled") => {
    try {
      await api.updateDebt(d.id, { status });
      await load();
    } catch (err: any) {
      Alert.alert("Error", err?.message || "Couldn't update");
    }
  };

  const confirmDelete = (d: Debt) => {
    Alert.alert("Delete this debt?", `${d.person} — ${formatINR(d.amount)}`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await api.deleteDebt(d.id);
            await load();
          } catch (err: any) {
            Alert.alert("Error", err?.message || "Couldn't delete");
          }
        },
      },
    ]);
  };

  // ── rendering ──
  const renderItem = ({ item }: { item: Debt }) => {
    const gave = item.direction === "lent";
    const isPending = item.status === "pending";
    const accent = gave ? C.success : C.warning;
    return (
      <View style={styles.item}>
        <View style={styles.itemTop}>
          <View style={styles.itemInfo}>
            <View style={styles.itemNameRow}>
              <Text style={styles.person} numberOfLines={1}>
                {item.person}
              </Text>
              <View style={[styles.chip, { borderColor: accent }]}>
                <Text style={[styles.chipText, { color: accent }]}>{gave ? "I gave" : "I got"}</Text>
              </View>
            </View>
            {!!item.reason && (
              <Text style={styles.reason} numberOfLines={2}>
                {item.reason}
              </Text>
            )}
            <Text style={styles.meta}>
              {gave ? "Given" : "Got"} {formatDate(item.date)}
              {!isPending && item.settled_on
                ? `  ·  ${gave ? "Returned" : "Paid back"} ${formatDate(item.settled_on)}`
                : ""}
            </Text>
          </View>
          <Text style={[styles.amount, { color: isPending ? accent : C.textMuted }]}>{formatINR(item.amount)}</Text>
        </View>

        <View style={styles.itemActions}>
          {isPending ? (
            <TouchableOpacity style={[styles.actionBtn, { backgroundColor: C.accent }]} onPress={() => setStatus(item, "settled")}>
              <Text style={styles.actionBtnText}>{gave ? "✓ Got it back" : "✓ Paid back"}</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity style={[styles.actionBtn, styles.actionGhost]} onPress={() => setStatus(item, "pending")}>
              <Text style={[styles.actionBtnText, { color: C.textSecondary }]}>Undo</Text>
            </TouchableOpacity>
          )}
          <TouchableOpacity style={styles.deleteBtn} onPress={() => confirmDelete(item)}>
            <Text style={styles.deleteText}>✕</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  if (loading) {
    return (
      <View style={[styles.container, styles.center]}>
        <ActivityIndicator color={C.accent} size="large" />
      </View>
    );
  }

  if (!book) {
    return (
      <View style={[styles.container, styles.center]}>
        <Text style={styles.emptyEmoji}>📖</Text>
        <Text style={styles.emptyTitle}>{loadError || "No book yet"}</Text>
        <Text style={styles.emptySub}>
          {loadError ? "Check your connection and try again." : "Create a book on the Home tab first — debts are kept inside a book."}
        </Text>
      </View>
    );
  }

  return (
    <View ref={kbRef} style={[styles.container, { paddingBottom: overlap }]}>
      {/* What you'll get / what you owe */}
      <View style={styles.summary}>
        <View style={styles.summaryCol}>
          <Text style={styles.summaryLabel}>YOU'LL GET</Text>
          <Text style={[styles.summaryAmount, { color: C.success }]}>{formatINR(willGet)}</Text>
        </View>
        <View style={styles.summaryDivider} />
        <View style={styles.summaryCol}>
          <Text style={styles.summaryLabel}>YOU OWE</Text>
          <Text style={[styles.summaryAmount, { color: C.warning }]}>{formatINR(owe)}</Text>
        </View>
      </View>
      <Text style={styles.bookLine}>in “{book.name}”</Text>

      <TouchableOpacity style={styles.addBtn} onPress={openForm} activeOpacity={0.8}>
        <Text style={styles.addBtnText}>＋ Add debt</Text>
      </TouchableOpacity>

      <View style={styles.segment}>
        {(["pending", "settled"] as const).map((t) => (
          <TouchableOpacity key={t} style={[styles.segmentBtn, tab === t && { backgroundColor: C.accent }]} onPress={() => setTab(t)}>
            <Text style={[styles.segmentText, { color: tab === t ? "#FFFFFF" : C.textMuted }]}>
              {t === "pending" ? `Pending (${pending.length})` : `Returned (${settled.length})`}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <FlatList
        data={shown}
        keyExtractor={(d) => String(d.id)}
        renderItem={renderItem}
        contentContainerStyle={styles.list}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyEmoji}>{tab === "pending" ? "🎉" : "🧾"}</Text>
            <Text style={styles.emptyTitle}>
              {tab === "pending"
                ? debts.length === 0
                  ? "No debts noted in this book"
                  : "Nothing pending"
                : "Nothing returned yet"}
            </Text>
            <Text style={styles.emptySub}>
              {debts.length === 0 ? "Tap “Add debt” to note money you gave or got." : ""}
            </Text>
          </View>
        }
      />

      {/* Add debt */}
      <Modal visible={formOpen} transparent statusBarTranslucent animationType="fade" onRequestClose={() => setFormOpen(false)}>
        <View ref={modalKb.ref} style={[styles.overlay, { paddingBottom: 24 + modalKb.overlap }]}>
          <View style={styles.formCard}>
            <Text style={styles.formTitle}>Add debt</Text>

            <View style={styles.dirRow}>
              {(["lent", "borrowed"] as const).map((dir) => {
                const on = direction === dir;
                const tint = dir === "lent" ? C.success : C.warning;
                return (
                  <TouchableOpacity
                    key={dir}
                    style={[styles.dirBtn, { borderColor: on ? tint : C.border, backgroundColor: on ? tint : C.bgInput }]}
                    onPress={() => setDirection(dir)}
                  >
                    <Text style={[styles.dirText, { color: on ? "#FFFFFF" : C.textSecondary }]}>
                      {dir === "lent" ? "I gave" : "I got"}
                    </Text>
                    <Text style={[styles.dirSub, { color: on ? "#FFFFFF" : C.textMuted }]}>
                      {dir === "lent" ? "they owe me" : "I owe them"}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>

            <Text style={styles.fieldLabel}>{direction === "lent" ? "Given to" : "Got from"}</Text>
            <TextInput
              style={styles.input}
              value={person}
              onChangeText={setPerson}
              placeholder="Person's name"
              placeholderTextColor={C.textMuted}
              maxLength={60}
              autoCapitalize="words"
            />

            <Text style={styles.fieldLabel}>Amount (₹)</Text>
            <TextInput
              style={styles.input}
              value={amount}
              onChangeText={setAmount}
              placeholder="0"
              placeholderTextColor={C.textMuted}
              keyboardType="numeric"
            />

            <Text style={styles.fieldLabel}>For what (optional)</Text>
            <TextInput
              style={styles.input}
              value={reason}
              onChangeText={setReason}
              placeholder="e.g. phone recharge"
              placeholderTextColor={C.textMuted}
              maxLength={200}
            />

            <Text style={styles.fieldLabel}>{direction === "lent" ? "Date given" : "Date got"} (YYYY-MM-DD)</Text>
            <TextInput
              style={styles.input}
              value={date}
              onChangeText={setDate}
              placeholder="YYYY-MM-DD"
              placeholderTextColor={C.textMuted}
              autoCapitalize="none"
              autoCorrect={false}
              maxLength={10}
            />

            {!!formError && <Text style={styles.formError}>{formError}</Text>}

            <View style={styles.formActions}>
              <TouchableOpacity style={styles.cancelBtn} onPress={() => setFormOpen(false)}>
                <Text style={styles.cancelText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.saveBtn, saving && { opacity: 0.6 }]} onPress={saveDebt} disabled={saving}>
                {saving ? <ActivityIndicator color="#FFFFFF" size="small" /> : <Text style={styles.saveText}>Save</Text>}
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const makeStyles = (C: Colors) =>
  StyleSheet.create({
    container: { flex: 1, backgroundColor: C.bg, paddingHorizontal: 16, paddingTop: 8 },
    center: { alignItems: "center", justifyContent: "center" },

    summary: {
      flexDirection: "row",
      backgroundColor: C.bgCard,
      borderRadius: 18,
      borderWidth: 1,
      borderColor: C.border,
      paddingVertical: 18,
    },
    summaryCol: { flex: 1, alignItems: "center" },
    summaryDivider: { width: 1, backgroundColor: C.border },
    summaryLabel: { color: C.textMuted, fontSize: 11, fontWeight: "700", letterSpacing: 1 },
    summaryAmount: { fontSize: 26, fontWeight: "800", marginTop: 4 },
    bookLine: { color: C.textMuted, fontSize: 12, textAlign: "center", marginTop: 8, marginBottom: 12 },

    addBtn: { backgroundColor: C.accent, borderRadius: 14, paddingVertical: 13, alignItems: "center", marginBottom: 12 },
    addBtnText: { color: "#FFFFFF", fontSize: 15, fontWeight: "700" },

    segment: {
      flexDirection: "row",
      backgroundColor: C.bgCard,
      borderRadius: 12,
      borderWidth: 1,
      borderColor: C.border,
      padding: 4,
      marginBottom: 12,
    },
    segmentBtn: { flex: 1, paddingVertical: 9, borderRadius: 9, alignItems: "center" },
    segmentText: { fontSize: 13, fontWeight: "700" },

    list: { paddingBottom: 24 },
    item: {
      backgroundColor: C.bgCard,
      borderRadius: 14,
      borderWidth: 1,
      borderColor: C.border,
      padding: 14,
      marginBottom: 10,
    },
    itemTop: { flexDirection: "row", alignItems: "flex-start" },
    itemInfo: { flex: 1, paddingRight: 10 },
    itemNameRow: { flexDirection: "row", alignItems: "center", gap: 8 },
    person: { color: C.textPrimary, fontSize: 16, fontWeight: "700", flexShrink: 1 },
    chip: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 1 },
    chipText: { fontSize: 10, fontWeight: "800", letterSpacing: 0.3 },
    reason: { color: C.textSecondary, fontSize: 13, marginTop: 4 },
    meta: { color: C.textMuted, fontSize: 12, marginTop: 5 },
    amount: { fontSize: 18, fontWeight: "800" },
    itemActions: { flexDirection: "row", alignItems: "center", marginTop: 12, gap: 10 },
    actionBtn: { flex: 1, borderRadius: 10, paddingVertical: 10, alignItems: "center" },
    actionGhost: { backgroundColor: C.bgInput },
    actionBtnText: { color: "#FFFFFF", fontSize: 13, fontWeight: "700" },
    deleteBtn: { paddingHorizontal: 12, paddingVertical: 8 },
    deleteText: { color: C.error, fontSize: 16, fontWeight: "700" },

    empty: { alignItems: "center", paddingVertical: 40 },
    emptyEmoji: { fontSize: 44, marginBottom: 10 },
    emptyTitle: { color: C.textSecondary, fontSize: 16, fontWeight: "600", textAlign: "center" },
    emptySub: { color: C.textMuted, fontSize: 13, marginTop: 4, textAlign: "center", paddingHorizontal: 24 },

    overlay: { flex: 1, backgroundColor: C.overlay, justifyContent: "center", padding: 24 },
    formCard: { backgroundColor: C.bgCard, borderRadius: 20, borderWidth: 1, borderColor: C.border, padding: 20 },
    formTitle: { color: C.textPrimary, fontSize: 20, fontWeight: "800", marginBottom: 14 },
    dirRow: { flexDirection: "row", gap: 10 },
    dirBtn: { flex: 1, borderWidth: 1, borderRadius: 12, paddingVertical: 10, alignItems: "center" },
    dirText: { fontSize: 15, fontWeight: "800" },
    dirSub: { fontSize: 11, marginTop: 1 },
    fieldLabel: {
      color: C.textSecondary,
      fontSize: 11,
      fontWeight: "700",
      letterSpacing: 0.5,
      textTransform: "uppercase",
      marginTop: 12,
      marginBottom: 5,
    },
    input: {
      backgroundColor: C.bgInput,
      color: C.textPrimary,
      borderRadius: 10,
      borderWidth: 1,
      borderColor: C.border,
      paddingHorizontal: 14,
      paddingVertical: 11,
      fontSize: 15,
    },
    formError: { color: C.error, fontSize: 13, fontWeight: "600", marginTop: 12 },
    formActions: { flexDirection: "row", justifyContent: "flex-end", alignItems: "center", gap: 10, marginTop: 18 },
    cancelBtn: { paddingHorizontal: 16, paddingVertical: 12 },
    cancelText: { color: C.textSecondary, fontSize: 15, fontWeight: "600" },
    saveBtn: { backgroundColor: C.accent, borderRadius: 10, paddingHorizontal: 26, paddingVertical: 12, minWidth: 90, alignItems: "center" },
    saveText: { color: "#FFFFFF", fontSize: 15, fontWeight: "700" },
  });
