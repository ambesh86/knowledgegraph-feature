import { extendTheme, type ThemeConfig } from "@chakra-ui/react";

/**
 * Atlas theme — a clean, light-first competitive-intelligence workspace with a
 * full dark mode. Neutral paper canvas, a restrained red brand accent for
 * identity, and a violet "intelligence" accent for AI affordances. All surface
 * / text / border tokens are semantic so components adapt across color modes
 * without per-component conditionals.
 */

const config: ThemeConfig = {
  initialColorMode: "light",
  useSystemColorMode: false,
  disableTransitionOnChange: true,
};

const atlasTheme = extendTheme({
  config,
  fonts: {
    heading: `'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif`,
    body: `'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif`,
    mono: `'JetBrains Mono', ui-monospace, SFMono-Regular, monospace`,
  },
  colors: {
    brand: {
      50: "#fff1f2",
      100: "#ffe1e3",
      200: "#ffc7cb",
      300: "#ff9aa2",
      400: "#fb6571",
      500: "#e11d2a", // CSL-style red
      600: "#c11522",
      700: "#a1121d",
      800: "#85131c",
      900: "#6f141c",
    },
    iris: {
      50: "#f1f0ff",
      100: "#e6e4ff",
      200: "#d0ccff",
      300: "#b1a8ff",
      400: "#8c7cf8",
      500: "#6d5efc", // AI / intelligence accent
      600: "#5b46e8",
      700: "#4c39c4",
      800: "#3f31a0",
      900: "#362d7f",
    },
    moss: { 500: "#16a34a", 600: "#15803d" }, // score up / positive
    amber: { 500: "#d97706" }, // medium priority
  },
  semanticTokens: {
    colors: {
      "bg.canvas": { _light: "#fbfbfc", _dark: "#0c0e13" },
      "bg.panel": { _light: "#ffffff", _dark: "#13161d" },
      "bg.subtle": { _light: "#f5f6f8", _dark: "#181c25" },
      "bg.hover": { _light: "#f0f1f4", _dark: "#1c2230" },
      "bg.active": { _light: "#eaecf0", _dark: "#222a3a" },
      "bg.inverse": { _light: "#16181d", _dark: "#f5f6f8" },
      "border.subtle": { _light: "#eceef1", _dark: "#222632" },
      "border.default": { _light: "#e2e5ea", _dark: "#2b3140" },
      "border.strong": { _light: "#d2d6de", _dark: "#3a4150" },
      "text.primary": { _light: "#15181d", _dark: "#eef0f4" },
      "text.secondary": { _light: "#3d434e", _dark: "#c3c9d4" },
      "text.muted": { _light: "#697080", _dark: "#8b93a3" },
      "text.subtle": { _light: "#969cab", _dark: "#646c7d" },
      "text.inverse": { _light: "#ffffff", _dark: "#15181d" },
      "accent.brand": { _light: "brand.500", _dark: "brand.400" },
      "accent.iris": { _light: "iris.500", _dark: "iris.400" },
      "priority.high": { _light: "#dc2626", _dark: "#f87171" },
      "priority.med": { _light: "#d97706", _dark: "#fbbf24" },
      "priority.low": { _light: "#64748b", _dark: "#94a3b8" },
      "score.up": { _light: "#16a34a", _dark: "#4ade80" },
      "score.down": { _light: "#dc2626", _dark: "#f87171" },
    },
  },
  styles: {
    global: {
      "html, body": {
        bg: "bg.canvas",
        color: "text.primary",
        fontFeatureSettings: '"cv11", "ss01"',
        WebkitFontSmoothing: "antialiased",
      },
      "*::selection": { bg: "iris.200", color: "iris.900" },
      "::-webkit-scrollbar": { width: "10px", height: "10px" },
      "::-webkit-scrollbar-thumb": {
        bg: "border.strong",
        borderRadius: "full",
        border: "2px solid transparent",
        backgroundClip: "content-box",
      },
      "::-webkit-scrollbar-track": { bg: "transparent" },
    },
  },
  radii: { card: "14px", chip: "9999px" },
  shadows: {
    card: "0 1px 2px rgba(16,18,23,0.04), 0 1px 3px rgba(16,18,23,0.06)",
    pop: "0 12px 40px -12px rgba(16,18,23,0.25)",
    focus: "0 0 0 3px rgba(109,94,252,0.35)",
  },
  components: {
    Button: {
      baseStyle: { fontWeight: 600, borderRadius: "10px" },
      variants: {
        solid: {
          bg: "accent.iris",
          color: "white",
          _hover: { bg: "iris.600", _disabled: { bg: "accent.iris" } },
          _active: { bg: "iris.700" },
        },
        brand: {
          bg: "accent.brand",
          color: "white",
          _hover: { bg: "brand.600" },
          _active: { bg: "brand.700" },
        },
        subtle: {
          bg: "bg.subtle",
          color: "text.secondary",
          _hover: { bg: "bg.hover" },
        },
        ghost: {
          color: "text.secondary",
          _hover: { bg: "bg.hover" },
        },
        outline: {
          borderColor: "border.default",
          color: "text.secondary",
          _hover: { bg: "bg.hover" },
        },
      },
    },
    Input: {
      defaultProps: { focusBorderColor: "iris.500" },
    },
  },
});

export default atlasTheme;
