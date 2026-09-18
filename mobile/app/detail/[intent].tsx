/**
 * detail/[intent].tsx — Detail screen for a specific intent.
 *
 * Header with intent emoji + total. FlatList of entries.
 * Long-press to edit or delete. Intent edit triggers PATCH (learning).
 */

import React, { useState, useCallback } from "react";
import { useMemo } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Alert,
  TextInput,
  Modal,
  ActivityIndicator,
} from "react-native";
import { useLocalSearchParams, useNavigation, useFocusEffect } from "expo-router";
import * as api from "../../src/api";
import { useApp } from "../../src/AppContext";
import { Colors } from "../../src/theme";
import { useKeyboardOverlap } from "../../src/useKeyboardOverlap";
import { formatINR, formatDate } from "../../src/helpers";
import { Expense, IntentMeta } from "../../src/types";

export default function DetailScreen() {
  const { colors: C } = useApp();
  const styles = useMemo(() => makeStyles(C), [C]);
  const { ref: kbRef, overlap } = useKeyboardOverlap();
  const modalKb = useKeyboardOverlap();
  const { intent, bookId } = useLocalSearchParams<{
    intent: string;
    bookId: string;
  }>();
  const navigation = useNavigation();

  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [intents, setIntents] = useState<IntentMeta[]>([]);

  // Edit modal
  const [editingExpense, setEditingExpense] = useState<Expense | null>(null);
  const [editAmount, setEditAmount] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editIntent, setEditIntent] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.getExpenses(undefined, intent, 1000, bookId ? Number(bookId) : undefined);
      setExpenses(data);
      setTotal(data.reduce((sum, e) => sum + Number(e.amount), 0));

      const ints = await api.getIntents();
      setIntents(ints);

      // Set header title
      const meta = ints.find((i) => i.intent === intent);
      if (meta) {
        navigation.setOptions({
          title: `${meta.emoji} ${meta.label}`,
        });
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [intent, bookId, navigation]);

  useFocusEffect(
    useCallback(() => {
      loadData();
    }, [loadData])
  );

  const handleLongPress = (expense: Expense) => {
    Alert.alert(expense.description, formatINR(expense.amount), [
      {
        text: "Edit",
        onPress: () => {
          setEditingExpense(expense);
          setEditAmount(String(expense.amount));
          setEditDesc(expense.description);
          setEditIntent(expense.intent);
        },
      },
      {
        text: "Delete",
        style: "destructive",
        onPress: () => handleDelete(expense.id),
      },
      { text: "Cancel", style: "cancel" },
    ]);
  };

  const handleDelete = async (id: number) => {
    try {
      await api.deleteExpense(id);
      loadData();
    } catch (err: any) {
      Alert.alert("Error", err.message);
    }
  };

  const handleSaveEdit = async () => {
    if (!editingExpense) return;

    try {
      const update: any = {};
      if (editAmount !== String(editingExpense.amount)) {
        update.amount = parseFloat(editAmount);
      }
      if (editDesc !== editingExpense.description) {
        update.description = editDesc;
      }
      if (editIntent !== editingExpense.intent) {
        update.intent = editIntent;
      }

      if (Object.keys(update).length > 0) {
        await api.updateExpense(editingExpense.id, update);
      }

      setEditingExpense(null);
      loadData();
    } catch (err: any) {
      Alert.alert("Error", err.message);
    }
  };

  const renderItem = ({ item }: { item: Expense }) => (
    <TouchableOpacity
      style={styles.expenseItem}
      onLongPress={() => handleLongPress(item)}
      activeOpacity={0.7}
    >
      <View style={styles.expenseInfo}>
        <Text style={styles.expenseDesc}>{item.description}</Text>
        <View style={styles.expenseMeta}>
          <Text style={styles.expenseDate}>{formatDate(item.spent_on)}</Text>
          {item.is_manual_override && (
            <View style={styles.overrideBadge}>
              <Text style={styles.overrideText}>Edited</Text>
            </View>
          )}
        </View>
      </View>
      <Text style={styles.expenseAmount}>{formatINR(item.amount)}</Text>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator color={C.accent} size="large" />
      </View>
    );
  }

  return (
    <View ref={kbRef} style={[styles.container, { paddingBottom: overlap }]}>
      {/* Header card */}
      <View style={styles.headerCard}>
        <Text style={styles.headerTotal}>{formatINR(total)}</Text>
        <Text style={styles.headerCount}>
          {expenses.length} {expenses.length === 1 ? "entry" : "entries"}
        </Text>
      </View>

      <Text style={styles.hint}>Long-press an entry to edit or delete</Text>

      <FlatList
        data={expenses}
        keyExtractor={(item) => String(item.id)}
        renderItem={renderItem}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.listContent}
        ListEmptyComponent={
          <View style={styles.emptyState}>
            <Text style={styles.emptyText}>No entries in this category</Text>
          </View>
        }
      />

      {/* Edit Modal */}
      <Modal
        visible={!!editingExpense}
        transparent
        statusBarTranslucent
        animationType="fade"
        onRequestClose={() => setEditingExpense(null)}
      >
        <View ref={modalKb.ref} style={[styles.modalOverlay, { paddingBottom: 24 + modalKb.overlap }]}>
          <View style={styles.modalCard}>
            <Text style={styles.modalTitle}>Edit Expense</Text>

            <Text style={styles.fieldLabel}>Description</Text>
            <TextInput
              style={styles.modalInput}
              value={editDesc}
              onChangeText={setEditDesc}
              placeholderTextColor={C.textMuted}
            />

            <Text style={styles.fieldLabel}>Amount (₹)</Text>
            <TextInput
              style={styles.modalInput}
              value={editAmount}
              onChangeText={setEditAmount}
              keyboardType="numeric"
              placeholderTextColor={C.textMuted}
            />

            <Text style={styles.fieldLabel}>Intent</Text>
            <FlatList
              data={intents}
              horizontal
              keyExtractor={(item) => item.intent}
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.intentPicker}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    styles.intentChip,
                    editIntent === item.intent && styles.intentChipActive,
                  ]}
                  onPress={() => setEditIntent(item.intent)}
                >
                  <Text style={styles.intentChipEmoji}>{item.emoji}</Text>
                  <Text
                    style={[
                      styles.intentChipLabel,
                      editIntent === item.intent &&
                        styles.intentChipLabelActive,
                    ]}
                  >
                    {item.label}
                  </Text>
                </TouchableOpacity>
              )}
            />

            <View style={styles.modalActions}>
              <TouchableOpacity
                style={styles.cancelBtn}
                onPress={() => setEditingExpense(null)}
              >
                <Text style={styles.cancelBtnText}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.saveEditBtn}
                onPress={handleSaveEdit}
              >
                <Text style={styles.saveEditBtnText}>Save</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

const makeStyles = (C: Colors) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: C.bg,
    paddingHorizontal: 16,
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: C.bg,
    justifyContent: "center",
    alignItems: "center",
  },
  headerCard: {
    backgroundColor: C.bgCard,
    borderRadius: 16,
    padding: 24,
    alignItems: "center",
    marginVertical: 16,
    borderWidth: 1,
    borderColor: C.border,
  },
  headerTotal: {
    color: C.textPrimary,
    fontSize: 32,
    fontWeight: "800",
  },
  headerCount: {
    color: C.textMuted,
    fontSize: 13,
    marginTop: 4,
  },
  hint: {
    color: C.textMuted,
    fontSize: 12,
    textAlign: "center",
    marginBottom: 12,
  },
  listContent: {
    paddingBottom: 24,
  },
  expenseItem: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: C.bgCard,
    borderRadius: 12,
    padding: 14,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: C.border,
  },
  expenseInfo: {
    flex: 1,
  },
  expenseDesc: {
    color: C.textPrimary,
    fontSize: 15,
    fontWeight: "600",
  },
  expenseMeta: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginTop: 4,
  },
  expenseDate: {
    color: C.textMuted,
    fontSize: 12,
  },
  overrideBadge: {
    backgroundColor: "rgba(56, 189, 248, 0.15)",
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  overrideText: {
    color: C.accent,
    fontSize: 10,
    fontWeight: "600",
  },
  expenseAmount: {
    color: C.accent,
    fontSize: 17,
    fontWeight: "700",
    marginLeft: 12,
  },
  emptyState: {
    alignItems: "center",
    paddingVertical: 40,
  },
  emptyText: {
    color: C.textMuted,
    fontSize: 14,
  },
  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: C.overlay,
    justifyContent: "center",
    padding: 24,
  },
  modalCard: {
    backgroundColor: C.bgCard,
    borderRadius: 20,
    padding: 24,
    borderWidth: 1,
    borderColor: C.border,
  },
  modalTitle: {
    color: C.textPrimary,
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 20,
  },
  fieldLabel: {
    color: C.textSecondary,
    fontSize: 12,
    fontWeight: "600",
    marginBottom: 6,
    marginTop: 12,
    textTransform: "uppercase",
    letterSpacing: 0.5,
  },
  modalInput: {
    backgroundColor: C.bgInput,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: C.textPrimary,
    fontSize: 15,
    borderWidth: 1,
    borderColor: C.border,
  },
  intentPicker: {
    paddingVertical: 8,
    gap: 6,
  },
  intentChip: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: C.bgInput,
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderWidth: 1,
    borderColor: C.border,
    gap: 4,
  },
  intentChipActive: {
    backgroundColor: C.accent,
    borderColor: C.accent,
  },
  intentChipEmoji: {
    fontSize: 14,
  },
  intentChipLabel: {
    color: C.textSecondary,
    fontSize: 12,
    fontWeight: "600",
  },
  intentChipLabelActive: {
    color: "#FFF",
  },
  modalActions: {
    flexDirection: "row",
    justifyContent: "flex-end",
    gap: 12,
    marginTop: 24,
  },
  cancelBtn: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 10,
  },
  cancelBtnText: {
    color: C.textSecondary,
    fontSize: 15,
    fontWeight: "600",
  },
  saveEditBtn: {
    backgroundColor: C.accent,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 10,
  },
  saveEditBtnText: {
    color: "#FFF",
    fontSize: 15,
    fontWeight: "700",
  },
});
