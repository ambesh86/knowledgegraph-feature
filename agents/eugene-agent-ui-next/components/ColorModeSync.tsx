"use client";

import { useEffect } from "react";
import { useColorMode } from "@chakra-ui/react";

/**
 * Mirrors the Chakra color mode onto `<body data-theme="...">` so the global
 * CSS ambient gradient (defined in app/globals.css) tracks the user's choice.
 */
export function ColorModeSync() {
  const { colorMode } = useColorMode();
  useEffect(() => {
    document.body.dataset.theme = colorMode;
  }, [colorMode]);
  return null;
}
