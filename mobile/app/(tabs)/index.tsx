/**
 * index.tsx — Home screen.
 *
 * Book name/total card, quick-add input with a category dropdown, and an
 * interactive spreadsheet-style table (Date | Amount | Description) for
 * every expense in the active book. Tap any cell to edit it inline.
 * If no book exists yet, prompts to create one before anything else.
 */

import React, { useState, useEffect, useCallback, useRef } from "react";
import { useMemo } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  Alert,
  ActivityIndicator,
  Keyboard,
  Animated,
  Modal,
  ScrollView,
} from "react-native";
import { useFocusEffect } from "expo-router";
import * as api from "../../src/api";
import { useApp } from "../../src/AppContext";
import { Colors } from "../../src/theme";
import { useKeyboardOverlap } from "../../src/useKeyboardOverlap";
import { formatINR, getCurrentMonth, formatMonth, formatDate } from "../../src/helpers";
import { Expense, Book, IntentMeta } from "../../src/types";

type EditingCell = { id: number; field: "date" | "amount" | "description" } | null;

export default function HomeScreen() {
  const { colors: C, setPendingDebts } = useApp();
  const styles = useMemo(() => makeStyles(C), [C]);
  const { ref: kbRef, overlap, keyboardOpen } = useKeyboardOverlap();
  const modalKb = useKeyboardOverlap();
  const [inputText, setInputText] = useState("");
  const [intents, setIntents] = useState<IntentMeta[]>([]);
  const [selectedIntent, setSelectedIntent] = useState<string | null>(null);
  const [bookLoading, setBookLoading] = useState(true);
  const [activeBook, setActiveBook] = useState<Book | null>(null);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [online, setOnline] = useState(true);
  const [pendingCount, setPendingCount] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  // New-book prompt (shown when there is no active book)
  const [newBookName, setNewBookName] = useState(formatMonth(getCurrentMonth()));
  const [creatingBook, setCreatingBook] = useState(false);

  // Book switcher modal
  const [switcherVisible, setSwitcherVisible] = useState(false);
  const [allBooks, setAllBooks] = useState<Book[]>([]);
  const [switcherNewName, setSwitcherNewName] = useState("");

  // Inline cell editing
  const [editingCell, setEditingCell] = useState<EditingCell>(null);
  const [editValue, setEditValue] = useState("");

  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, { toValue: 1.02, duration: 2000, useNativeDriver: true }),
        Animated.timing(pulseAnim, { toValue: 1, duration: 2000, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  const loadData = useCallback(async () => {
    setBookLoading(true);
    try {
      const book = await api.getActiveBook();
      setActiveBook(book);
      setPendingDebts(book?.pending_debts ?? 0);
      setOnline(true);
      api.getIntents().then(setIntents).catch(() => {});

      if (book) {
        const rows = await api.getExpenses(undefined, undefined, 1000, book.id);
        setExpenses(rows);
      } else {
        setExpenses([]);
      }
    } catch {
      setOnline(false);
    } finally {
      setBookLoading(false);
    }

    const queue = await api.getPendingQueue();
    setPendingCount(queue.length);
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadData();
    }, [loadData])
  );

  useEffect(() => {
    const unsub = api.onConnectivityChange((isOnline) => {
      setOnline(isOnline);
      if (isOnline) {
        api.flushQueue().then((flushed) => {
          if (flushed > 0) loadData();
        });
      }
    });
    return unsub;
  }, [loadData]);

  // ── Create / switch book ──
  const handleCreateBook = async () => {
    const name = newBookName.trim();
    if (!name) return;
    setCreatingBook(true);
    try {
      await api.createBook(name);
      await loadData();
    } catch (err: any) {
      Alert.alert("Error", err.message || "Failed to create book");
    } finally {
      setCreatingBook(false);
    }
  };

  const openSwitcher = async () => {
    try {
      const books = await api.getBooks();
      setAllBooks(books);
      setSwitcherVisible(true);
    } catch (err: any) {
      Alert.alert("Error", err.message || "Failed to load books");
    }
  };

  const handleSelectBook = async (book: Book) => {
    try {
      await api.setActiveBook(book.id);
      setSwitcherVisible(false);
      await loadData();
    } catch (err: any) {
      Alert.alert("Error", err.message);
    }
  };

  const handleCreateBookFromSwitcher = async () => {
    const name = switcherNewName.trim();
    if (!name) return;
    try {
      await api.createBook(name);
      setSwitcherNewName("");
      setSwitcherVisible(false);
      await loadData();
    } catch (err: any) {
      Alert.alert("Error", err.message);
    }
  };

  // ── Quick add ──
  const handleTextChange = (text: string) => {
    setInputText(text);
    if (!text.trim()) setSelectedIntent(null);
  };

  const showDropdown = inputText.trim().length > 0 && !selectedIntent;
  const selectedMeta = intents.find((i) => i.intent === selectedIntent);

  const handleSubmit = async () => {
    const text = inputText.trim();
    if (!text) return;
    if (!selectedIntent) {
      Alert.alert("Pick a category", "Choose a category from the list before adding.");
      return;
    }

    setSubmitting(true);
    Keyboard.dismiss();

    try {
      const result = await api.createExpense(text, selectedIntent);
      setInputText("");
      setSelectedIntent(null);
      if (result) {
        loadData();
      } else {
        setPendingCount((c) => c + 1);
        Alert.alert("📦 Queued", "You're offline. Entry saved and will sync when connected.");
      }
    } catch (err: any) {
      Alert.alert("Error", err.message || "Failed to add expense");
    } finally {
      setSubmitting(false);
    }
  };

  // ── Inline cell editing ──
  const startEdit = (expense: Expense, field: "date" | "amount" | "description") => {
    const raw =
      field === "date" ? expense.spent_on : field === "amount" ? String(expense.amount) : expense.description;
    setEditingCell({ id: expense.id, field });
    setEditValue(raw);
  };

  const cancelEdit = () => {
    setEditingCell(null);
    setEditValue("");
  };

  const commitEdit = async () => {
    if (!editingCell) return;
    const { id, field } = editingCell;
    const value = editValue.trim();
    setEditingCell(null);

    const expense = expenses.find((e) => e.id === id);
    if (!expense || !value) return;

    const patch: { amount?: number; description?: string; date?: string } = {};
    if (field === "amount") {
      const n = parseFloat(value);
      if (isNaN(n) || n <= 0) {
        Alert.alert("Invalid amount", "Enter a number greater than 0.");
        return;
      }
      if (n === Number(expense.amount)) return;
      patch.amount = n;
    } else if (field === "description") {
      if (value === expense.description) return;
      patch.description = value;
    } else if (field === "date") {
      if (value === expense.spent_on) return;
      patch.date = value;
    }

    try {
      const updated = await api.updateExpense(id, patch);
      setExpenses((rows) => rows.map((r) => (r.id === id ? updated : r)));
    } catch (err: any) {
      Alert.alert("Error", err.message || "Failed to save change");
    }
  };

  const handleDeleteRow = (expense: Expense) => {
    Alert.alert("Delete entry", `${expense.description} — ${formatINR(expense.amount)}`, [
      { text: "Cancel", style: "cancel" },
      {
        text: "Delete",
        style: "destructive",
        onPress: async () => {
          try {
            await api.deleteExpense(expense.id);
            setExpenses((rows) => rows.filter((r) => r.id !== expense.id));
          } catch (err: any) {
            Alert.alert("Error", err.message);
          }
        },
      },
    ]);
  };

  const getIntentEmoji = (intent: string): string => {
    const emojis: Record<string, string> = {
      food: "🍛", tea_snacks: "☕", petrol: "⛽", movie: "🎬", fruits_diet: "🍎",
      transport: "🚗", bills_recharge: "📱", medical: "💊", grooming: "💈",
      rent: "🏠", education: "📚", grocery: "🛒", purchase: "🛍️", others: "📦",
    };
    return emojis[intent] || "📦";
  };

  // Derived from the live `expenses` list (not activeBook.total/count) so
  // inline edits/deletes/adds reflect immediately without a re-fetch.
  const bookTotal = expenses.reduce((sum, e) => sum + Number(e.amount), 0);
  const bookCount = expenses.length;

  // ── No active book yet: prompt to create one before anything else ──
  if (!bookLoading && !activeBook) {
    return (
      <View ref={kbRef} style={[styles.container, { paddingBottom: overlap }]}>
        <View style={styles.createBookCard}>
          <Text style={styles.createBookEmoji}>📖</Text>
          <Text style={styles.createBookTitle}>Start a book</Text>
          <Text style={styles.createBookSubtitle}>
            Give this expense book a name — a month, a trip, anything.
          </Text>
          <TextInput
            style={styles.createBookInput}
            value={newBookName}
            onChangeText={setNewBookName}
            placeholder="e.g. September 2026"
            placeholderTextColor={C.textMuted}
            autoCapitalize="words"
          />
          <TouchableOpacity
            style={[styles.createBookBtn, (!newBookName.trim() || creatingBook) && styles.addButtonDisabled]}
            onPress={handleCreateBook}
            disabled={!newBookName.trim() || creatingBook}
          >
            {creatingBook ? (
              <ActivityIndicator color="#FFF" size="small" />
            ) : (
              <Text style={styles.createBookBtnText}>Create Book</Text>
            )}
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  return (
    <View ref={kbRef} style={[styles.container, { paddingBottom: overlap }]}>
      {(!online || pendingCount > 0) && (
        <View style={styles.offlineBanner}>
          <Text style={styles.offlineText}>
            {!online ? "⚡ Offline" : ""}
            {pendingCount > 0 ? ` — ${pendingCount} pending` : ""}
          </Text>
        </View>
      )}

      {/* Book card — tap to switch/create. Hidden while typing to make room. */}
      {!keyboardOpen && (
        <TouchableOpacity onPress={openSwitcher} activeOpacity={0.8}>
          <Animated.View style={[styles.totalCard, { transform: [{ scale: pulseAnim }] }]}>
            <Text style={styles.totalLabel}>{activeBook?.name?.toUpperCase() ?? "THIS MONTH"} ▾</Text>
            <Text style={styles.totalAmount}>{formatINR(bookTotal)}</Text>
            <Text style={styles.totalCount}>{bookCount} {bookCount === 1 ? "entry" : "entries"}</Text>
          </Animated.View>
        </TouchableOpacity>
      )}

      {/* Input area */}
      <View style={styles.inputContainer}>
        <TextInput
          style={styles.input}
          placeholder='Type expense... e.g. "tea 20"'
          placeholderTextColor={C.textMuted}
          value={inputText}
          onChangeText={handleTextChange}
          onSubmitEditing={handleSubmit}
          returnKeyType="send"
          autoCorrect={false}
          autoCapitalize="none"
        />
        <TouchableOpacity
          style={[styles.addButton, (submitting || !inputText.trim() || !selectedIntent) && styles.addButtonDisabled]}
          onPress={handleSubmit}
          disabled={submitting || !inputText.trim() || !selectedIntent}
          activeOpacity={0.7}
        >
          {submitting ? <ActivityIndicator color="#FFF" size="small" /> : <Text style={styles.addButtonText}>+</Text>}
        </TouchableOpacity>
      </View>

      {showDropdown && (
        <View style={styles.dropdown}>
          <Text style={styles.dropdownTitle}>Choose a category</Text>
          <ScrollView style={[styles.dropdownList, keyboardOpen && { maxHeight: 170 }]} keyboardShouldPersistTaps="handled" nestedScrollEnabled>
            {intents.length === 0 ? (
              <Text style={styles.dropdownEmpty}>Loading categories…</Text>
            ) : (
              intents.map((i) => (
                <TouchableOpacity
                  key={i.intent}
                  style={styles.dropdownItem}
                  onPress={() => setSelectedIntent(i.intent)}
                >
                  <Text style={styles.dropdownEmoji}>{i.emoji}</Text>
                  <Text style={styles.dropdownLabel}>{i.label}</Text>
                </TouchableOpacity>
              ))
            )}
          </ScrollView>
        </View>
      )}

      {selectedMeta && (
        <TouchableOpacity style={styles.selectedChip} onPress={() => setSelectedIntent(null)}>
          <Text style={styles.selectedChipText}>
            {selectedMeta.emoji}  {selectedMeta.label}
          </Text>
          <Text style={styles.selectedChipChange}>Change ▾</Text>
        </TouchableOpacity>
      )}

      {/* Table */}
      <View style={styles.tableHeaderRow}>
        <Text style={[styles.tableHeaderCell, styles.colDate]}>Date</Text>
        <Text style={[styles.tableHeaderCell, styles.colAmount]}>Amount</Text>
        <Text style={[styles.tableHeaderCell, styles.colDesc]}>Description</Text>
        <View style={styles.colDelete} />
      </View>

      {expenses.length === 0 ? (
        <View style={styles.emptyState}>
          <Text style={styles.emptyEmoji}>💰</Text>
          <Text style={styles.emptyText}>No expenses in this book yet</Text>
          <Text style={styles.emptySubtext}>Type something like "tea 20" above</Text>
        </View>
      ) : (
        <FlatList
          data={expenses}
          keyExtractor={(item) => String(item.id)}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.listContent}
          renderItem={({ item }) => {
            return (
              <View style={styles.tableRow}>
                {/* Date cell */}
                {editingCell?.id === item.id && editingCell.field === "date" ? (
                  <TextInput
                    style={[styles.cellInput, styles.colDate]}
                    value={editValue}
                    onChangeText={setEditValue}
                    onBlur={commitEdit}
                    onSubmitEditing={commitEdit}
                    autoFocus
                    placeholder="YYYY-MM-DD"
                    placeholderTextColor={C.textMuted}
                  />
                ) : (
                  <TouchableOpacity style={styles.colDate} onPress={() => startEdit(item, "date")}>
                    <Text style={styles.cellText}>{formatDate(item.spent_on)}</Text>
                  </TouchableOpacity>
                )}

                {/* Amount cell */}
                {editingCell?.id === item.id && editingCell.field === "amount" ? (
                  <TextInput
                    style={[styles.cellInput, styles.colAmount]}
                    value={editValue}
                    onChangeText={setEditValue}
                    onBlur={commitEdit}
                    onSubmitEditing={commitEdit}
                    keyboardType="numeric"
                    autoFocus
                  />
                ) : (
                  <TouchableOpacity style={styles.colAmount} onPress={() => startEdit(item, "amount")}>
                    <Text style={[styles.cellText, styles.cellAmountText]}>{formatINR(item.amount)}</Text>
                  </TouchableOpacity>
                )}

                {/* Description cell */}
                {editingCell?.id === item.id && editingCell.field === "description" ? (
                  <TextInput
                    style={[styles.cellInput, styles.colDesc]}
                    value={editValue}
                    onChangeText={setEditValue}
                    onBlur={commitEdit}
                    onSubmitEditing={commitEdit}
                    autoFocus
                  />
                ) : (
                  <TouchableOpacity style={styles.colDesc} onPress={() => startEdit(item, "description")}>
                    <Text style={styles.cellEmoji}>{getIntentEmoji(item.intent)}</Text>
                    <Text style={styles.cellText} numberOfLines={1}>{item.description}</Text>
                  </TouchableOpacity>
                )}

                <TouchableOpacity style={styles.colDelete} onPress={() => handleDeleteRow(item)}>
                  <Text style={styles.deleteText}>✕</Text>
                </TouchableOpacity>
              </View>
            );
          }}
        />
      )}

      {/* Book switcher modal */}
      <Modal visible={switcherVisible} transparent statusBarTranslucent animationType="fade" onRequestClose={() => setSwitcherVisible(false)}>
        <View ref={modalKb.ref} style={[styles.modalOverlay, { paddingBottom: 24 + modalKb.overlap }]}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Books</Text>
            <FlatList
              data={allBooks}
              keyExtractor={(b) => String(b.id)}
              style={{ maxHeight: modalKb.keyboardOpen ? 110 : 280 }}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[styles.bookRow, item.is_active && styles.bookRowActive]}
                  onPress={() => handleSelectBook(item)}
                >
                  <View style={{ flex: 1 }}>
                    <Text style={styles.bookRowName}>{item.name}</Text>
                    <Text style={styles.bookRowMeta}>{item.count} entries</Text>
                  </View>
                  <Text style={styles.bookRowTotal}>{formatINR(item.total)}</Text>
                </TouchableOpacity>
              )}
              ListEmptyComponent={<Text style={styles.emptyText}>No books yet</Text>}
            />

            <Text style={styles.fieldLabel}>New book</Text>
            <View style={styles.newBookRow}>
              <TextInput
                style={styles.modalInput}
                value={switcherNewName}
                onChangeText={setSwitcherNewName}
                placeholder="Name this book"
                placeholderTextColor={C.textMuted}
              />
              <TouchableOpacity style={styles.saveEditBtn} onPress={handleCreateBookFromSwitcher}>
                <Text style={styles.saveEditBtnText}>Create</Text>
              </TouchableOpacity>
            </View>

            <TouchableOpacity style={styles.cancelBtn} onPress={() => setSwitcherVisible(false)}>
              <Text style={styles.cancelBtnText}>Close</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const makeStyles = (C: Colors) => StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg, paddingHorizontal: 16, paddingTop: 8 },
  offlineBanner: {
    backgroundColor: C.offlineBg, borderWidth: 1, borderColor: C.offlineBorder,
    borderRadius: 8, paddingVertical: 6, paddingHorizontal: 12, marginBottom: 8,
  },
  offlineText: { color: C.error, fontSize: 12, fontWeight: "600", textAlign: "center" },
  totalCard: {
    backgroundColor: C.bgCard, borderRadius: 20, padding: 24, alignItems: "center", marginBottom: 16,
    borderWidth: 1, borderColor: C.border, shadowColor: "#38BDF8", shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1, shadowRadius: 16, elevation: 8,
  },
  totalLabel: { color: C.textSecondary, fontSize: 13, fontWeight: "600", letterSpacing: 1, marginBottom: 8 },
  totalAmount: { color: C.textPrimary, fontSize: 40, fontWeight: "800", letterSpacing: -1 },
  totalCount: { color: C.textMuted, fontSize: 13, marginTop: 6 },
  inputContainer: { flexDirection: "row", alignItems: "center", gap: 10, marginBottom: 8 },
  input: {
    flex: 1, backgroundColor: C.bgInput, borderRadius: 14, paddingHorizontal: 16, paddingVertical: 14,
    fontSize: 16, color: C.textPrimary, borderWidth: 1, borderColor: C.border,
  },
  addButton: {
    backgroundColor: C.accent, width: 50, height: 50, borderRadius: 14, alignItems: "center", justifyContent: "center",
    shadowColor: C.accent, shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 6,
  },
  addButtonDisabled: { opacity: 0.5 },
  addButtonText: { color: "#FFF", fontSize: 24, fontWeight: "700", lineHeight: 26 },
  dropdown: {
    backgroundColor: C.bgCard, borderRadius: 12, borderWidth: 1, borderColor: C.border,
    marginBottom: 12, paddingVertical: 6,
  },
  dropdownTitle: {
    color: C.textMuted, fontSize: 11, fontWeight: "700", letterSpacing: 0.8,
    textTransform: "uppercase", paddingHorizontal: 14, paddingVertical: 6,
  },
  dropdownList: { maxHeight: 230 },
  dropdownItem: { flexDirection: "row", alignItems: "center", paddingHorizontal: 14, paddingVertical: 11 },
  dropdownEmoji: { fontSize: 20, marginRight: 12 },
  dropdownLabel: { color: C.textPrimary, fontSize: 15, fontWeight: "600" },
  dropdownEmpty: { color: C.textMuted, fontSize: 13, paddingHorizontal: 14, paddingVertical: 10 },
  selectedChip: {
    flexDirection: "row", alignItems: "center", justifyContent: "space-between",
    backgroundColor: C.bgCard, borderRadius: 12, borderWidth: 1, borderColor: C.accent,
    paddingHorizontal: 14, paddingVertical: 10, marginBottom: 12,
  },
  selectedChipText: { color: C.textPrimary, fontSize: 15, fontWeight: "700" },
  selectedChipChange: { color: C.accent, fontSize: 13, fontWeight: "700" },

  // Table
  tableHeaderRow: {
    flexDirection: "row", paddingHorizontal: 10, paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: C.border,
  },
  tableHeaderCell: { color: C.textMuted, fontSize: 11, fontWeight: "700", textTransform: "uppercase", letterSpacing: 0.5 },
  colDate: { width: 82, justifyContent: "center" },
  colAmount: { width: 84, justifyContent: "center" },
  colDesc: { flex: 1, flexDirection: "row", alignItems: "center", paddingLeft: 8 },
  colDelete: { width: 28, alignItems: "center", justifyContent: "center" },
  tableRow: {
    flexDirection: "row", alignItems: "center", backgroundColor: C.bgCard, borderRadius: 10, marginBottom: 6,
    paddingVertical: 10, paddingHorizontal: 10, borderWidth: 1, borderColor: C.border,
  },
  cellText: { color: C.textPrimary, fontSize: 13 },
  cellAmountText: { color: C.accent, fontWeight: "700" },
  cellEmoji: { fontSize: 14, marginRight: 6 },
  cellInput: {
    color: C.textPrimary, fontSize: 13, backgroundColor: C.bgInput, borderRadius: 6, paddingHorizontal: 6,
    paddingVertical: 4, borderWidth: 1, borderColor: C.accent,
  },
  deleteText: { color: C.error, fontSize: 14, fontWeight: "700" },

  emptyState: { alignItems: "center", paddingVertical: 40 },
  emptyEmoji: { fontSize: 48, marginBottom: 12 },
  emptyText: { color: C.textSecondary, fontSize: 16, fontWeight: "600", textAlign: "center" },
  emptySubtext: { color: C.textMuted, fontSize: 13, marginTop: 4 },
  listContent: { paddingBottom: 20 },

  // Create-book prompt
  createBookCard: {
    flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 24,
  },
  createBookEmoji: { fontSize: 48, marginBottom: 12 },
  createBookTitle: { color: C.textPrimary, fontSize: 22, fontWeight: "800", marginBottom: 6 },
  createBookSubtitle: { color: C.textSecondary, fontSize: 14, textAlign: "center", marginBottom: 20 },
  createBookInput: {
    width: "100%", backgroundColor: C.bgInput, borderRadius: 14, paddingHorizontal: 16, paddingVertical: 14,
    fontSize: 16, color: C.textPrimary, borderWidth: 1, borderColor: C.border, marginBottom: 14, textAlign: "center",
  },
  createBookBtn: {
    backgroundColor: C.accent, borderRadius: 14, paddingHorizontal: 32, paddingVertical: 14, alignItems: "center",
  },
  createBookBtnText: { color: "#FFF", fontSize: 16, fontWeight: "700" },

  // Book switcher modal
  modalOverlay: { flex: 1, backgroundColor: C.overlay, justifyContent: "center", padding: 24 },
  modalCard: { backgroundColor: C.bgCard, borderRadius: 20, padding: 24, borderWidth: 1, borderColor: C.border },
  modalTitle: { color: C.textPrimary, fontSize: 20, fontWeight: "700", marginBottom: 16 },
  bookRow: {
    flexDirection: "row", alignItems: "center", backgroundColor: C.bgInput, borderRadius: 10, padding: 12,
    marginBottom: 8, borderWidth: 1, borderColor: C.border,
  },
  bookRowActive: { borderColor: C.accent },
  bookRowName: { color: C.textPrimary, fontSize: 14, fontWeight: "700" },
  bookRowMeta: { color: C.textMuted, fontSize: 12, marginTop: 2 },
  bookRowTotal: { color: C.accent, fontSize: 14, fontWeight: "700" },
  fieldLabel: {
    color: C.textSecondary, fontSize: 12, fontWeight: "600", marginTop: 16, marginBottom: 6,
    textTransform: "uppercase", letterSpacing: 0.5,
  },
  newBookRow: { flexDirection: "row", gap: 10 },
  modalInput: {
    flex: 1, backgroundColor: C.bgInput, borderRadius: 10, paddingHorizontal: 14, paddingVertical: 12,
    color: C.textPrimary, fontSize: 15, borderWidth: 1, borderColor: C.border,
  },
  saveEditBtn: { backgroundColor: C.accent, paddingHorizontal: 20, borderRadius: 10, justifyContent: "center" },
  saveEditBtnText: { color: "#FFF", fontSize: 14, fontWeight: "700" },
  cancelBtn: { alignItems: "center", paddingVertical: 14, marginTop: 12 },
  cancelBtnText: { color: C.textSecondary, fontSize: 15, fontWeight: "600" },
});
