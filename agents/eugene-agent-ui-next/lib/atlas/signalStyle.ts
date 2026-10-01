import {
  LuBookOpen,
  LuBuilding2,
  LuFlaskConical,
  LuLandmark,
  LuScale,
  LuSignal,
} from "react-icons/lu";
import type { IconType } from "react-icons";
import type { SignalType } from "@/lib/atlas/seed";

/**
 * A colour and an icon per signal type.
 *
 * Radar mixes five kinds of evidence in one ranked list, and they are not
 * interchangeable: a phase-3 trial readout and a corporate filing call for
 * different reading. Before this, every row looked identical and the only way to
 * tell them apart was to read the small grey word "Publication" — so an analyst
 * scanning the page had no way to skip to the trials.
 *
 * Hue carries type, never priority. Priority already has its own badge and its own
 * red/amber/grey scale, and two colour systems competing for the same meaning is
 * how a page stops being readable. Colour here is a redundant cue: every type also
 * carries its icon and its name, so nothing is lost in greyscale or to a
 * colour-blind reader.
 *
 * Each type declares light and dark values explicitly rather than relying on one
 * colour to work in both. A mid-tone that reads well on white goes muddy on the
 * dark canvas, and these are the accent hues doing the most work on the page.
 */

export interface TypeTone {
  /** Text and icon colour. */
  fg: string;
  /** Chip fill. */
  bg: string;
  /** Chip border and the row's left rail. */
  border: string;
}

export interface TypeMeta {
  label: string;
  icon: IconType;
  light: TypeTone;
  dark: TypeTone;
}

export const SIGNAL_TYPE_META: Record<SignalType, TypeMeta> = {
  Trial: {
    label: "Trial",
    icon: LuFlaskConical,
    light: { fg: "#1d4ed8", bg: "rgba(37,99,235,0.10)", border: "rgba(37,99,235,0.34)" },
    dark: { fg: "#93b4ff", bg: "rgba(96,148,255,0.16)", border: "rgba(96,148,255,0.38)" },
  },
  Patent: {
    label: "Patent",
    icon: LuScale,
    light: { fg: "#b45309", bg: "rgba(217,119,6,0.12)", border: "rgba(217,119,6,0.34)" },
    dark: { fg: "#fbbf24", bg: "rgba(251,191,36,0.14)", border: "rgba(251,191,36,0.36)" },
  },
  Publication: {
    label: "Publication",
    icon: LuBookOpen,
    light: { fg: "#0f766e", bg: "rgba(15,118,110,0.10)", border: "rgba(15,118,110,0.32)" },
    dark: { fg: "#5eead4", bg: "rgba(94,234,212,0.13)", border: "rgba(94,234,212,0.34)" },
  },
  Regulatory: {
    label: "Regulatory",
    icon: LuLandmark,
    light: { fg: "#6d28d9", bg: "rgba(109,40,217,0.10)", border: "rgba(109,40,217,0.32)" },
    dark: { fg: "#c4b5fd", bg: "rgba(196,181,253,0.14)", border: "rgba(196,181,253,0.34)" },
  },
  Corporate: {
    label: "Corporate",
    icon: LuBuilding2,
    light: { fg: "#be123c", bg: "rgba(190,18,60,0.09)", border: "rgba(190,18,60,0.30)" },
    dark: { fg: "#fda4af", bg: "rgba(253,164,175,0.13)", border: "rgba(253,164,175,0.32)" },
  },
};

/** Neutral fallback, so an unrecognised type still renders as a real row. */
const UNKNOWN: TypeMeta = {
  label: "Signal",
  icon: LuSignal,
  light: { fg: "#4b5563", bg: "rgba(75,85,99,0.09)", border: "rgba(75,85,99,0.28)" },
  dark: { fg: "#cbd5e1", bg: "rgba(203,213,225,0.12)", border: "rgba(203,213,225,0.30)" },
};

export function typeMeta(type: string): TypeMeta {
  return SIGNAL_TYPE_META[type as SignalType] ?? UNKNOWN;
}

export function typeTone(type: string, mode: "light" | "dark"): TypeTone {
  return typeMeta(type)[mode];
}

/**
 * Score band colour. Deliberately the priority scale, not the type scale — the
 * meter answers "how urgent", which is the same question the priority badge
 * answers, so they must agree.
 */
export function scoreTone(score: number, mode: "light" | "dark"): string {
  if (score >= 70) return mode === "light" ? "#dc2626" : "#f87171";
  if (score >= 50) return mode === "light" ? "#d97706" : "#fbbf24";
  return mode === "light" ? "#64748b" : "#94a3b8";
}
