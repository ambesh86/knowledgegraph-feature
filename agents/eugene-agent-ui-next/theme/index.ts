import { extendTheme, type ThemeConfig } from "@chakra-ui/react";

const config: ThemeConfig = {
  initialColorMode: "dark",
  useSystemColorMode: false,
  disableTransitionOnChange: false,
};

/**
 * 2026 theme — "Aurora".
 *
 * Dark-first.  Refined three-stop accent gradient (cyan → indigo → magenta)
 * sampled from Aurora Borealis palettes in agentic-AI dashboards from late
 * 2025 (Linear's analytics, Vercel v0, Supabase Studio, Neo4j Aura context).
 *
 * Surface ramp tightened around #0a0d14 → #1f2433 to give the canvas more
 * contrast against accent splashes; ink ramp pushed warmer (slight cyan
 * tint) so body text stays comfortable against a dark gradient hero.
 */
const theme = extendTheme({
  config,
  fonts: {
    heading: `'Geist', 'Inter', ui-sans-serif, system-ui`,
    body: `'Geist', 'Inter', ui-sans-serif, system-ui`,
    mono: `'JetBrains Mono', 'Fira Code', ui-monospace, SFMono-Regular, monospace`,
  },
  colors: {
    // ── Surface ramp (bg) ────────────────────────────────────────────
    surface: {
      0: "#06080d",      // canvas
      50: "#0a0d14",
      100: "#0f1320",
      200: "#161b2b",
      300: "#1d2336",
      400: "#262e44",
      500: "#343d57",
    },
    // ── Ink ramp (text/borders) ──────────────────────────────────────
    ink: {
      50: "#f6f9ff",
      100: "#dbe3f5",
      200: "#a9b4cf",
      300: "#7d88a6",
      400: "#5a647f",
      500: "#3a4258",
    },
    // ── Aurora accent (primary CTA gradient stop 2 of 3) ─────────────
    accent: {
      50: "#eef2ff",
      100: "#d7deff",
      200: "#aab6ff",
      300: "#7d8eff",
      400: "#5d70ff",
      500: "#4256f5",     // primary
      600: "#3140cc",
      700: "#252fa0",
      800: "#1c2480",
      900: "#141a64",
    },
    // ── Aurora cyan (gradient stop 1) ────────────────────────────────
    cyan: {
      50: "#e0fbff",
      100: "#b8f2ff",
      200: "#7de4ff",
      300: "#3dd0f5",
      400: "#1bb8e0",      // primary cyan
      500: "#0e98bd",
      600: "#0c7a9a",
      700: "#0a5e78",
    },
    // ── Aurora magenta (gradient stop 3) ─────────────────────────────
    magenta: {
      50: "#ffe7f6",
      100: "#ffb9e3",
      200: "#ff86cc",
      300: "#ff52b3",
      400: "#ff2a9d",      // primary magenta
      500: "#e21383",
      600: "#b40a69",
      700: "#86054c",
    },
    // ── Lumen (success / progress) ───────────────────────────────────
    lumen: {
      300: "#9af5dc",
      400: "#5fe9c4",
      500: "#27d3a5",
      600: "#13a880",
    },
    // ── Semantic signals ─────────────────────────────────────────────
    signal: {
      success: "#27d3a5",
      warning: "#ffc561",
      danger: "#ff5e7a",
      info: "#5d70ff",
    },
  },
  semanticTokens: {
    colors: {
      "bg.canvas": { default: "surface.0", _light: "#f6f9ff" },
      "bg.panel": { default: "surface.100", _light: "#ffffff" },
      "bg.surface": { default: "surface.200", _light: "#eef2f8" },
      "bg.elevated": { default: "surface.300", _light: "#ffffff" },
      "bg.glass": {
        default: "rgba(15, 19, 32, 0.78)",
        _light: "rgba(255,255,255,0.88)",
      },
      "bg.aurora": {
        // Subtle background hero gradient — used behind heading bands.
        default:
          "linear-gradient(135deg, rgba(27,184,224,0.10) 0%, rgba(66,86,245,0.12) 50%, rgba(255,42,157,0.10) 100%)",
        _light:
          "linear-gradient(135deg, rgba(27,184,224,0.07) 0%, rgba(66,86,245,0.10) 50%, rgba(255,42,157,0.07) 100%)",
      },
      "border.subtle": { default: "whiteAlpha.100", _light: "blackAlpha.100" },
      "border.muted": { default: "whiteAlpha.200", _light: "blackAlpha.200" },
      "border.strong": { default: "whiteAlpha.300", _light: "blackAlpha.300" },
      "text.primary": { default: "ink.50", _light: "#0d1220" },
      "text.muted": { default: "ink.200", _light: "#5a647f" },
      "text.subtle": { default: "ink.300", _light: "#7d88a6" },
      "accent.solid": { default: "accent.400", _light: "accent.500" },
      "accent.cyan": { default: "cyan.400", _light: "cyan.500" },
      "accent.magenta": { default: "magenta.400", _light: "magenta.500" },
    },
  },
  styles: {
    global: (props: { colorMode: "light" | "dark" }) => ({
      "html, body, #__next": {
        height: "100%",
        bg: "bg.canvas",
        color: "text.primary",
        fontFeatureSettings: `"cv02","cv03","cv04","cv11"`,
        transition: "background-color 200ms ease, color 200ms ease",
      },
      "::selection": { bg: "accent.500", color: "white" },
      "*::-webkit-scrollbar": { width: "8px", height: "8px" },
      "*::-webkit-scrollbar-thumb": {
        bg: props.colorMode === "dark" ? "whiteAlpha.200" : "blackAlpha.200",
        borderRadius: "full",
      },
      "*::-webkit-scrollbar-thumb:hover": {
        bg: props.colorMode === "dark" ? "whiteAlpha.400" : "blackAlpha.400",
      },
    }),
  },
  components: {
    Button: {
      defaultProps: { colorScheme: "accent" },
      baseStyle: { borderRadius: "xl", fontWeight: 500 },
    },
    Input: { defaultProps: { variant: "filled" } },
    Textarea: { defaultProps: { variant: "filled" } },
    Tabs: {
      defaultProps: { variant: "soft-rounded", colorScheme: "accent" },
    },
  },
});

export default theme;
