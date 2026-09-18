/**
 * summary.tsx — Summary screen.
 *
 * One card per intent with emoji, label, total, %, progress bar vs budget,
 * scoped to the active book (same book shown on Home — not a calendar
 * month, since books are user-named periods that can span any dates).
 * Tapping a card opens the Detail screen filtered to that book.
 */

import React, { useState, useCallback } from "react";
import { useMemo } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { useRouter, useFocusEffect } from "expo-router";
import * as api from "../../src/api";
import { useApp } from "../../src/AppContext";
import { Colors } from "../../src/theme";
import { formatINR } from "../../src/helpers";
import { IntentSummary, MonthlySummary, Book } from "../../src/types";

export default function SummaryScreen() {
  const { colors: C } = useApp();
  const styles = useMemo(() => makeStyles(C), [C]);
  const router = useRouter();
  const [book, setBook] = useState<Book | null>(null);
  const [summary, setSummary] = useState<MonthlySummary | null>(null);
  const [loading, setLoading] = useState(true);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    try {
      const activeBook = await api.getActiveBook();
      setBook(activeBook);
      if (activeBook) {
        const data = await api.getMonthlySummary(undefined, activeBook.id);
        setSummary(data);
      } else {
        setSummary(null);
      }
    } catch (err) {
      console.error("Failed to load summary:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadSummary();
    }, [loadSummary])
  );

  const handleIntentPress = (intent: string) => {
    if (!book) return;
    router.push({
      pathname: "/detail/[intent]",
      params: { intent, bookId: String(book.id) },
    });
  };

  const renderIntentCard = (item: IntentSummary) => {
    const progressPercent =
      item.budget_limit && item.budget_limit > 0
        ? Math.min((Number(item.total) / Number(item.budget_limit)) * 100, 100)
        : item.percent;

    const isOverBudget =
      !!item.budget_limit && Number(item.total) > Number(item.budget_limit);

    return (
      <TouchableOpacity
        key={item.intent}
        style={styles.intentCard}
        onPress={() => handleIntentPress(item.intent)}
        activeOpacity={0.7}
      >
        <View style={styles.intentHeader}>
          <View style={styles.intentLeft}>
            <Text style={styles.intentEmoji}>{item.emoji}</Text>
            <View>
              <Text style={styles.intentLabel}>{item.label}</Text>
              <Text style={styles.intentCount}>
                {item.count} {item.count === 1 ? "entry" : "entries"}
              </Text>
            </View>
          </View>
          <View style={styles.intentRight}>
            <Text style={styles.intentTotal}>{formatINR(item.total)}</Text>
            <Text style={styles.intentPercent}>{item.percent}%</Text>
          </View>
        </View>

        {/* Progress bar */}
        <View style={styles.progressContainer}>
          <View style={styles.progressBg}>
            <View
              style={[
                styles.progressFill,
                {
                  width: `${Math.min(progressPercent, 100)}%`,
                  backgroundColor: isOverBudget ? "#EF4444" : item.colour,
                },
              ]}
            />
          </View>
          {item.budget_limit ? (
            <Text
              style={[
                styles.budgetText,
                isOverBudget && styles.overBudgetText,
              ]}
            >
              {isOverBudget ? "Over!" : formatINR(item.remaining || 0) + " left"}
            </Text>
          ) : null}
        </View>
      </TouchableOpacity>
    );
  };

  if (!loading && !book) {
    return (
      <View style={styles.container}>
        <View style={styles.emptyBookState}>
          <Text style={styles.emptyBookEmoji}>📖</Text>
          <Text style={styles.emptyBookText}>No book yet</Text>
          <Text style={styles.emptyBookSubtext}>
            Create one on the Home tab to start tracking expenses.
          </Text>
        </View>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Book name */}
      <View style={styles.bookHeader}>
        <Text style={styles.bookHeaderText}>{book?.name ?? ""}</Text>
      </View>

      {/* Total */}
      {summary && (
        <View style={styles.totalBar}>
          <Text style={styles.totalLabel}>Total Spent</Text>
          <Text style={styles.totalAmount}>{formatINR(summary.total)}</Text>
        </View>
      )}

      {loading ? (
        <ActivityIndicator
          color={C.accent}
          size="large"
          style={{ marginTop: 40 }}
        />
      ) : (
        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
        >
          {summary?.intents
            .filter((i) => i.total > 0 || i.intent !== "others")
            .map(renderIntentCard)}
        </ScrollView>
      )}
    </View>
  );
}

const makeStyles = (C: Colors) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: C.bg,
    paddingHorizontal: 16,
  },
  bookHeader: {
    alignItems: "center",
    paddingVertical: 16,
  },
  bookHeaderText: {
    color: C.textPrimary,
    fontSize: 20,
    fontWeight: "700",
    textAlign: "center",
  },
  emptyBookState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 24,
  },
  emptyBookEmoji: {
    fontSize: 48,
    marginBottom: 12,
  },
  emptyBookText: {
    color: C.textSecondary,
    fontSize: 16,
    fontWeight: "600",
  },
  emptyBookSubtext: {
    color: C.textMuted,
    fontSize: 13,
    marginTop: 4,
    textAlign: "center",
  },
  totalBar: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: C.bgCard,
    borderRadius: 14,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: C.border,
  },
  totalLabel: {
    color: C.textSecondary,
    fontSize: 14,
    fontWeight: "500",
  },
  totalAmount: {
    color: C.textPrimary,
    fontSize: 24,
    fontWeight: "800",
  },
  scrollContent: {
    paddingBottom: 24,
  },
  intentCard: {
    backgroundColor: C.bgCard,
    borderRadius: 14,
    padding: 16,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: C.border,
  },
  intentHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  intentLeft: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  intentEmoji: {
    fontSize: 28,
  },
  intentLabel: {
    color: C.textPrimary,
    fontSize: 16,
    fontWeight: "700",
  },
  intentCount: {
    color: C.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  intentRight: {
    alignItems: "flex-end",
  },
  intentTotal: {
    color: C.textPrimary,
    fontSize: 18,
    fontWeight: "700",
  },
  intentPercent: {
    color: C.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  progressContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  progressBg: {
    flex: 1,
    height: 6,
    backgroundColor: C.border,
    borderRadius: 3,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: 3,
  },
  budgetText: {
    color: C.textMuted,
    fontSize: 11,
    fontWeight: "600",
    minWidth: 70,
    textAlign: "right",
  },
  overBudgetText: {
    color: "#EF4444",
  },
});
