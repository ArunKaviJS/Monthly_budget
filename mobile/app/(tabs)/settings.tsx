/**
 * settings.tsx — Settings screen.
 *
 * Per-intent monthly budget, view/clear learned keywords,
 * export data as CSV/JSON, delete all expenses.
 */

import React, { useState, useCallback, useEffect } from "react";
import { useMemo } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
  Alert,
  FlatList,
} from "react-native";
import { useFocusEffect } from "expo-router";
import * as api from "../../src/api";
import { useApp } from "../../src/AppContext";
import { Colors } from "../../src/theme";
import { useKeyboardOverlap } from "../../src/useKeyboardOverlap";
import { formatINR } from "../../src/helpers";
import { IntentMeta, Budget, LearnedKeyword } from "../../src/types";

export default function SettingsScreen() {
  const { colors: C } = useApp();
  const styles = useMemo(() => makeStyles(C), [C]);
  const { ref: kbRef, overlap } = useKeyboardOverlap();
  const [intents, setIntents] = useState<IntentMeta[]>([]);
  const [budgets, setBudgets] = useState<Record<string, string>>({});
  const [keywords, setKeywords] = useState<LearnedKeyword[]>([]);
  const [section, setSection] = useState<"budgets" | "keywords" | "export">(
    "budgets"
  );

  const loadSettings = useCallback(async () => {
    try {
      const ints = await api.getIntents();
      setIntents(ints);
      const buds = await api.getBudgets();
      const budMap: Record<string, string> = {};
      buds.forEach((b) => (budMap[b.intent] = String(b.monthly_limit)));
      setBudgets(budMap);
    } catch {}

    try {
      const kws = await api.getKeywords();
      setKeywords(kws);
    } catch {}
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadSettings();
    }, [loadSettings])
  );

  const handleSaveBudget = async (intent: string) => {
    const value = budgets[intent];
    if (!value || isNaN(parseFloat(value))) return;
    try {
      await api.setBudget(intent, parseFloat(value));
      Alert.alert("✅ Saved", `Budget for ${intent} set to ₹${value}`);
    } catch (err: any) {
      Alert.alert("Error", err.message);
    }
  };

  const handleDeleteKeyword = async (keyword: string) => {
    try {
      await api.deleteKeyword(keyword);
      setKeywords((kws) => kws.filter((k) => k.keyword !== keyword));
    } catch {}
  };

  const handleClearKeywords = () => {
    Alert.alert("Clear All Keywords", "This will remove all learned keywords.", [
      { text: "Cancel", style: "cancel" },
      {
        text: "Clear",
        style: "destructive",
        onPress: async () => {
          try {
            await api.clearKeywords();
            setKeywords([]);
            Alert.alert("✅ Cleared", "All learned keywords removed");
          } catch {}
        },
      },
    ]);
  };

  const handleExport = async (format: "json" | "csv") => {
    try {
      const data = await api.exportData(format);
      Alert.alert(
        `📦 Export (${format.toUpperCase()})`,
        data.length > 500 ? data.slice(0, 500) + "..." : data
      );
    } catch (err: any) {
      Alert.alert("Error", err.message);
    }
  };

  const handleDeleteAllExpenses = () => {
    Alert.alert(
      "Delete All Expenses",
      "This permanently deletes every expense and frees the disk space used by them. This cannot be undone.",
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Delete All",
          style: "destructive",
          onPress: async () => {
            try {
              const count = await api.deleteAllExpenses();
              Alert.alert("✅ Deleted", `${count} expense(s) removed.`);
            } catch (err: any) {
              Alert.alert("Error", err.message);
            }
          },
        },
      ]
    );
  };

  return (
    <View ref={kbRef} style={{ flex: 1, backgroundColor: C.bg, paddingBottom: overlap }}>
    <ScrollView style={styles.container} contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
      {/* Section tabs */}
      <View style={styles.tabRow}>
        {(["budgets", "keywords", "export"] as const).map((s) => (
          <TouchableOpacity
            key={s}
            style={[styles.tab, section === s && styles.tabActive]}
            onPress={() => setSection(s)}
          >
            <Text
              style={[styles.tabText, section === s && styles.tabTextActive]}
            >
              {s === "budgets" ? "💰 Budgets" : s === "keywords" ? "🧠 Keywords" : "📦 Export"}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Budgets */}
      {section === "budgets" && (
        <View style={styles.section}>
          <Text style={styles.sectionSubtitle}>
            Set monthly limits per category
          </Text>
          {intents
            .filter((i) => i.intent !== "others")
            .map((intent) => (
              <View key={intent.intent} style={styles.budgetRow}>
                <Text style={styles.budgetEmoji}>{intent.emoji}</Text>
                <Text style={styles.budgetLabel}>{intent.label}</Text>
                <TextInput
                  style={styles.budgetInput}
                  value={budgets[intent.intent] || ""}
                  onChangeText={(v) =>
                    setBudgets({ ...budgets, [intent.intent]: v })
                  }
                  placeholder="₹"
                  placeholderTextColor={C.textMuted}
                  keyboardType="numeric"
                  onEndEditing={() => handleSaveBudget(intent.intent)}
                  onBlur={() => handleSaveBudget(intent.intent)}
                  onSubmitEditing={() => handleSaveBudget(intent.intent)}
                />
              </View>
            ))}
        </View>
      )}

      {/* Keywords */}
      {section === "keywords" && (
        <View style={styles.section}>
          <View style={styles.keywordsHeader}>
            <Text style={styles.sectionSubtitle}>
              Learned from your corrections ({keywords.length})
            </Text>
            {keywords.length > 0 && (
              <TouchableOpacity onPress={handleClearKeywords}>
                <Text style={styles.clearText}>Clear All</Text>
              </TouchableOpacity>
            )}
          </View>
          {keywords.length === 0 ? (
            <Text style={styles.emptyText}>
              No learned keywords yet. The app learns when you correct an
              intent.
            </Text>
          ) : (
            keywords.map((kw) => (
              <View key={kw.keyword} style={styles.keywordRow}>
                <View style={styles.keywordInfo}>
                  <Text style={styles.keywordText}>{kw.keyword}</Text>
                  <Text style={styles.keywordIntent}>
                    → {kw.intent} ({kw.hits} hits)
                  </Text>
                </View>
                <TouchableOpacity
                  onPress={() => handleDeleteKeyword(kw.keyword)}
                >
                  <Text style={styles.deleteText}>✕</Text>
                </TouchableOpacity>
              </View>
            ))
          )}
        </View>
      )}

      {/* Export */}
      {section === "export" && (
        <View style={styles.section}>
          <Text style={styles.sectionSubtitle}>Download your data</Text>
          <View style={styles.exportRow}>
            <TouchableOpacity
              style={styles.exportBtn}
              onPress={() => handleExport("csv")}
            >
              <Text style={styles.exportBtnText}>📄 Export CSV</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={styles.exportBtn}
              onPress={() => handleExport("json")}
            >
              <Text style={styles.exportBtnText}>📋 Export JSON</Text>
            </TouchableOpacity>
          </View>

          <Text style={[styles.sectionSubtitle, { marginTop: 24 }]}>
            Danger Zone
          </Text>
          <TouchableOpacity
            style={styles.dangerBtn}
            onPress={handleDeleteAllExpenses}
          >
            <Text style={styles.dangerBtnText}>🗑️ Delete All Expenses</Text>
          </TouchableOpacity>
        </View>
      )}
    </ScrollView>
    </View>
  );
}

const makeStyles = (C: Colors) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: C.bg,
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },
  section: {
    marginBottom: 24,
  },
  sectionTitle: {
    color: C.textPrimary,
    fontSize: 18,
    fontWeight: "700",
    marginBottom: 12,
  },
  sectionSubtitle: {
    color: C.textSecondary,
    fontSize: 13,
    marginBottom: 12,
  },
  tabRow: {
    flexDirection: "row",
    gap: 8,
    marginBottom: 20,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    backgroundColor: C.bgCard,
    alignItems: "center",
    borderWidth: 1,
    borderColor: C.border,
  },
  tabActive: {
    backgroundColor: C.accent,
    borderColor: C.accent,
  },
  tabText: {
    color: C.textMuted,
    fontSize: 12,
    fontWeight: "600",
  },
  tabTextActive: {
    color: "#FFF",
  },
  budgetRow: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: C.bgCard,
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: C.border,
    gap: 10,
  },
  budgetEmoji: {
    fontSize: 20,
  },
  budgetLabel: {
    flex: 1,
    color: C.textPrimary,
    fontSize: 14,
    fontWeight: "600",
  },
  budgetInput: {
    width: 90,
    backgroundColor: C.bgInput,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 8,
    color: C.textPrimary,
    fontSize: 14,
    textAlign: "right",
    borderWidth: 1,
    borderColor: C.border,
  },
  keywordsHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 12,
  },
  clearText: {
    color: C.error,
    fontSize: 13,
    fontWeight: "600",
  },
  emptyText: {
    color: C.textMuted,
    fontSize: 13,
    textAlign: "center",
    paddingVertical: 20,
  },
  keywordRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: C.bgCard,
    borderRadius: 10,
    padding: 12,
    marginBottom: 6,
    borderWidth: 1,
    borderColor: C.border,
  },
  keywordInfo: {
    flex: 1,
  },
  keywordText: {
    color: C.textPrimary,
    fontSize: 14,
    fontWeight: "600",
  },
  keywordIntent: {
    color: C.textMuted,
    fontSize: 12,
    marginTop: 2,
  },
  deleteText: {
    color: C.error,
    fontSize: 18,
    fontWeight: "700",
    paddingHorizontal: 8,
  },
  exportRow: {
    flexDirection: "row",
    gap: 12,
  },
  exportBtn: {
    flex: 1,
    backgroundColor: C.bgCard,
    borderRadius: 12,
    padding: 16,
    alignItems: "center",
    borderWidth: 1,
    borderColor: C.border,
  },
  exportBtnText: {
    color: C.textPrimary,
    fontSize: 14,
    fontWeight: "600",
  },
  dangerBtn: {
    backgroundColor: C.dangerBg,
    borderRadius: 12,
    padding: 14,
    alignItems: "center",
    borderWidth: 1,
    borderColor: C.error,
  },
  dangerBtnText: {
    color: C.error,
    fontSize: 14,
    fontWeight: "700",
  },
});
