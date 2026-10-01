"use client";

import { ChakraProvider, ColorModeScript } from "@chakra-ui/react";
import theme from "@/theme/atlas";
import { AtlasAuthProvider } from "@/lib/atlas/useAuth";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <>
      <ColorModeScript initialColorMode={theme.config.initialColorMode} />
      <ChakraProvider theme={theme}>
        <AtlasAuthProvider>{children}</AtlasAuthProvider>
      </ChakraProvider>
    </>
  );
}
