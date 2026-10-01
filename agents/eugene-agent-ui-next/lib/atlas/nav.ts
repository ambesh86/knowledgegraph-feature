import type { IconType } from "react-icons";
import {
  LuLayoutGrid,
  LuMessagesSquare,
  LuFlaskConical,
  LuRadar,
  LuListChecks,
  LuTarget,
  LuLibrary,
  LuFileText,
  LuSettings,
} from "react-icons/lu";

export interface NavItem {
  id: string;
  label: string;
  path: string;
  icon: IconType;
  shortcut?: string; // digit for ⌘<n>
  hint: string;
}

/** Primary navigation — drives the sidebar, command palette, and ⌘1–8. */
export const NAV: NavItem[] = [
  { id: "today", label: "Today", path: "/today", icon: LuLayoutGrid, shortcut: "1", hint: "Your daily intelligence briefing" },
  { id: "ask", label: "Ask", path: "/ask", icon: LuMessagesSquare, shortcut: "2", hint: "Graph-grounded research chat" },
  // Use Case 2. Named for what it produces rather than the activity: an analyst
  // looks for the diligence brief, not for "research".
  { id: "research", label: "Diligence", path: "/research", icon: LuFlaskConical, shortcut: "3", hint: "On-demand scientific due diligence on a target" },
  { id: "radar", label: "Radar", path: "/radar", icon: LuRadar, shortcut: "4", hint: "Continuous competitive monitoring" },
  { id: "watchlist", label: "Watchlist", path: "/watchlist", icon: LuListChecks, shortcut: "5", hint: "Live-ranked company portfolio" },
  // Sits directly after Watchlist: it is the ranked-companies view turned into a
  // document, and reading it right after scanning the list is the natural order.
  { id: "briefing", label: "Briefing", path: "/briefing", icon: LuFileText, shortcut: "6", hint: "Weekly ranked partnership briefing" },
  { id: "programs", label: "Programs", path: "/programs", icon: LuTarget, shortcut: "7", hint: "Strategic priorities & target profiles" },
  { id: "library", label: "Library", path: "/library", icon: LuLibrary, shortcut: "8", hint: "Briefs, decisions & institutional memory" },
];

export const SETTINGS_ITEM: NavItem = {
  id: "settings",
  label: "Settings",
  path: "/settings",
  icon: LuSettings,
  hint: "Preferences, sources & account",
};

export const ALL_NAV = [...NAV, SETTINGS_ITEM];
