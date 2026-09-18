/**
 * SplashOverlay.tsx — Black opening screen.
 *
 * The initials "JSA" are "signed" in Yellowtail: a left-to-right wipe reveals
 * them, the white fades out toward the right, and an underline stroke draws
 * beneath. Then a faded "by Arun" appears at the bottom centre and the whole
 * screen fades away.
 *
 * Built only from plain React Native views + a gradient (no SVG masks), so it
 * draws identically on every Android/iOS phone.
 */

import React, { useEffect, useRef, useState } from "react";
import { Animated, Easing, StyleSheet, Text, View } from "react-native";
import { LinearGradient } from "expo-linear-gradient";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { useFonts, Yellowtail_400Regular } from "@expo-google-fonts/yellowtail";

const SIG_W = 300;
const SIG_H = 150;
const LINE_W = 210;

export default function SplashOverlay({ onDone }: { onDone: () => void }) {
  const insets = useSafeAreaInsets();
  const [fontLoaded, fontError] = useFonts({ Yellowtail_400Regular });

  const overlayOpacity = useRef(new Animated.Value(1)).current;
  const creditOpacity = useRef(new Animated.Value(0)).current;
  const write = useRef(new Animated.Value(0)).current;
  const underline = useRef(new Animated.Value(0)).current;

  // Don't wait on the font forever (slow connection / first launch): after
  // 1.5s the signature starts anyway and switches to Yellowtail when it lands.
  const [waited, setWaited] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setWaited(true), 1500);
    return () => clearTimeout(t);
  }, []);
  const ready = fontLoaded || !!fontError || waited;

  useEffect(() => {
    if (!ready) return;
    Animated.sequence([
      Animated.parallel([
        Animated.timing(write, {
          toValue: 1,
          duration: 1500,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: false,
        }),
        Animated.sequence([
          Animated.delay(1000),
          Animated.timing(underline, {
            toValue: 1,
            duration: 800,
            easing: Easing.out(Easing.quad),
            useNativeDriver: false,
          }),
        ]),
      ]),
      Animated.timing(creditOpacity, { toValue: 0.75, duration: 800, useNativeDriver: true }),
      Animated.delay(900),
      Animated.timing(overlayOpacity, { toValue: 0, duration: 600, useNativeDriver: true }),
    ]).start(({ finished }) => {
      if (finished) onDone();
    });
  }, [ready]);

  const revealWidth = write.interpolate({ inputRange: [0, 1], outputRange: [0, SIG_W] });
  const lineWidth = underline.interpolate({ inputRange: [0, 1], outputRange: [0, LINE_W] });

  return (
    <Animated.View style={[styles.overlay, { opacity: overlayOpacity }]} pointerEvents="auto">
      <View style={styles.signature}>
        {/* Wipe: this box grows from the left; the letters inside stay put. */}
        <Animated.View style={[styles.reveal, { width: revealWidth }]}>
          <View style={styles.inkBox}>
            <Text
              style={[styles.ink, fontLoaded && { fontFamily: "Yellowtail_400Regular" }]}
              numberOfLines={1}
              allowFontScaling={false}
            >
              JSA
            </Text>
            {/* White fades away toward the right */}
            <LinearGradient
              pointerEvents="none"
              colors={["rgba(0,0,0,0)", "rgba(0,0,0,0)", "rgba(0,0,0,0.86)"]}
              locations={[0, 0.45, 1]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={StyleSheet.absoluteFill}
            />
          </View>
        </Animated.View>

        {/* Underline stroke, drawn left to right */}
        <Animated.View style={[styles.lineWrap, { width: lineWidth }]}>
          <LinearGradient
            colors={["rgba(255,255,255,0.95)", "rgba(255,255,255,0.8)", "rgba(255,255,255,0.08)"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.line}
          />
        </Animated.View>
      </View>

      <View style={[styles.creditWrap, { bottom: 40 + insets.bottom }]}>
        <Animated.Text style={[styles.credit, { opacity: creditOpacity }]}>by Arun</Animated.Text>
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFill,
    backgroundColor: "#000000",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  signature: {
    width: SIG_W,
    alignItems: "flex-start",
    transform: [{ rotate: "-5deg" }],
  },
  reveal: {
    height: SIG_H,
    overflow: "hidden",
  },
  inkBox: {
    width: SIG_W,
    height: SIG_H,
    alignItems: "center",
    justifyContent: "center",
  },
  ink: {
    width: SIG_W,
    color: "#FFFFFF",
    fontSize: 112,
    lineHeight: 140,
    textAlign: "center",
    includeFontPadding: false,
    textShadowColor: "rgba(255,255,255,0.28)",
    textShadowOffset: { width: 0, height: 0 },
    textShadowRadius: 14,
  },
  lineWrap: {
    marginLeft: (SIG_W - LINE_W) / 2,
    marginTop: -6,
    height: 3,
    overflow: "hidden",
    borderRadius: 2,
  },
  line: {
    width: LINE_W,
    height: 3,
    borderRadius: 2,
  },
  creditWrap: {
    position: "absolute",
    left: 0,
    right: 0,
    alignItems: "center",
  },
  credit: {
    color: "#FFFFFF",
    fontSize: 15,
    letterSpacing: 3,
    fontWeight: "300",
  },
});
