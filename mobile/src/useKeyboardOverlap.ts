/**
 * useKeyboardOverlap.ts — Keeps what you're typing visible.
 *
 * On current Android (edge-to-edge) the keyboard is drawn *over* the app
 * instead of pushing it up. This hook measures how much of a container the
 * keyboard covers; add it as bottom padding and the content lifts by exactly
 * that much. On phones/OS versions that already resize the window, the
 * container ends up above the keyboard, the overlap is 0, and nothing moves
 * twice.
 *
 *   const { ref, overlap, keyboardOpen } = useKeyboardOverlap();
 *   <View ref={ref} style={{ flex: 1, paddingBottom: overlap }}>…</View>
 */

import { useEffect, useRef, useState } from "react";
import { Dimensions, Keyboard, KeyboardEvent, Platform, View } from "react-native";

export function useKeyboardOverlap() {
  const ref = useRef<View>(null);
  const [overlap, setOverlap] = useState(0);
  const [keyboardOpen, setKeyboardOpen] = useState(false);

  useEffect(() => {
    const showEvent = Platform.OS === "ios" ? "keyboardWillShow" : "keyboardDidShow";
    const hideEvent = Platform.OS === "ios" ? "keyboardWillHide" : "keyboardDidHide";

    const onShow = (e: KeyboardEvent) => {
      setKeyboardOpen(true);
      const keyboardTop =
        e.endCoordinates.screenY || Dimensions.get("screen").height - e.endCoordinates.height;
      ref.current?.measureInWindow((_x, y, _w, h) => {
        setOverlap(Math.max(0, Math.round(y + h - keyboardTop)));
      });
    };
    const onHide = () => {
      setKeyboardOpen(false);
      setOverlap(0);
    };

    const showSub = Keyboard.addListener(showEvent, onShow);
    const hideSub = Keyboard.addListener(hideEvent, onHide);
    return () => {
      showSub.remove();
      hideSub.remove();
    };
  }, []);

  return { ref, overlap, keyboardOpen };
}
