# mobile — technical detail

## Stack (package.json)
expo ~57.0.24, react 19.2.3, react-native 0.86.3, expo-router ~57.0.22, react-native-reanimated 4.5.1
(+ worklets 0.10.1), gesture-handler, screens, safe-area-context, expo-secure-store,
@react-native-async-storage/async-storage 2.2.0, expo-linear-gradient, @expo-google-fonts/yellowtail,
expo-build-properties, `query-string ^7.1.3` (pinned for a runtime error seen with newer versions),
TypeScript ~6.0.3 (strict). Entry: `index.ts` -> `expo-router/entry`.

## Build / release
- `app.json`: name "Arun's Budget", slug `monthly-budget`, owner `arunkavijs`, Android package
  `com.monthlybudget.app`, adaptive icon (bg `#0F172A`), `userInterfaceStyle: automatic`, plugins
  expo-router, expo-font, expo-splash-screen (black bg), expo-build-properties (`usesCleartextTraffic`),
  expo-secure-store; EAS project id set.
- `eas.json`: `preview` -> Android APK, internal distribution; `production` -> app-bundle;
  `appVersionSource: local` (bump `android.versionCode` in `app.json` manually for updates).
- Dev: `npm start` (Expo Go via LAN, Windows firewall must allow Metro), `npm run android`.
- Same keystore is kept remotely by EAS, so new APKs install over old ones.

## Navigation
expo-router file routes. Root `Stack` (screens `(tabs)`, `debts`, `detail/[intent]`) is keyed by the
signed-in user id so all screens remount on account change. Splash and auth are overlays rendered in
`_layout.tsx` above the stack, not routes. Tab bar height/padding add the bottom safe-area inset
(fixes the Android gesture bar covering tabs).

## State
- `AppContext`: `ready`, `mode/colors/setMode`, `authStatus` (`checking|signedOut|signedIn`), `user`,
  `startSession`, `signOut`, `pendingDebts/setPendingDebts`. No global store for books/expenses;
  each screen fetches on focus (`useFocusEffect`) and keeps local state.
- `api.ts` module-level state: `_token`, `_onUnauthorized`, `_isOnline` + listeners.

## Networking (`api.ts`)
`apiFetch` adds JSON headers + Bearer token, refuses non-public paths without a token, parses errors via
`extractDetail` (string detail, or first validation message with "Value error, " stripped), returns
`undefined` for 204. Successful response sets online; network-like errors set offline.
Offline queue: AsyncStorage `@budget_pending_queue`, flushed by `flushQueue` (sequential, stops on
first failure).

## Token storage
`authStorage`: SecureStore key `budget_auth_token` on native, AsyncStorage on web; cached user JSON in
AsyncStorage `@budget_user`. Token is replaced on every refresh.

## Android keyboard
Edge-to-edge Android draws the keyboard over content. `useKeyboardOverlap` listens to
`keyboardDidShow/Hide` (`keyboardWillShow/Hide` on iOS), measures the container with `measureInWindow`
and returns `overlap = max(0, bottom - keyboardTop)`; screens add it as `paddingBottom`. Modals use a
second hook instance and `statusBarTranslucent` so measurements are in window coordinates.

## Splash
Pure RN: an `Animated.View` whose width grows (JS-driven, `useNativeDriver: false`) reveals a fixed
"JSA" text; a `LinearGradient` overlay fades the white to the right; a second animated width draws the
underline; opacity animation for "by Arun" and the final fade. SVG masks were dropped because they did
not render on the target Android phone.

## Theme
`theme.ts` exports `darkColors`, `lightColors`, `spacing`, `radius`, `fonts`. Screens build styles with
`useMemo(() => makeStyles(C), [C])`.

## Type safety
`tsc` (strict) is the only static check; there are no JS tests in `mobile/`.
