"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Box,
  Button,
  Flex,
  FormControl,
  FormLabel,
  Heading,
  HStack,
  Input,
  InputGroup,
  InputRightElement,
  Select,
  Text,
  VStack,
  IconButton,
} from "@chakra-ui/react";
import { LuEye, LuEyeOff, LuArrowRight } from "react-icons/lu";
import { useAuth } from "@/lib/atlas/useAuth";
import { AREA_OPTIONS, DEFAULT_AREA } from "@/lib/atlas/areas";
import { AtlasMark } from "./AtlasMark";

type Mode = "signin" | "register";

export function LoginForm() {
  const router = useRouter();
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [focusArea, setFocusArea] = useState(DEFAULT_AREA);
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const nameRef = useRef<HTMLInputElement>(null);

  /**
   * Adopt anything typed or auto-filled before React hydrated.
   *
   * These inputs are controlled, so their value comes from state. Anything written
   * to the DOM before hydration — a password manager, Chrome autofill, a fast typist
   * on a slow connection — is silently discarded the moment React takes over and
   * renders `value=""` on top of it. The user sees their email vanish and gets
   * "Please fill out this field" on a form they know they completed.
   *
   * Reading the DOM once on mount and lifting whatever is there into state closes
   * the gap. Found via an e2e test whose fill landed mid-hydration, but the failure
   * is a real one for anyone whose browser fills this form for them.
   */
  useEffect(() => {
    const adopt = (
      ref: React.RefObject<HTMLInputElement>,
      setter: (v: string) => void
    ) => {
      const value = ref.current?.value;
      if (value) setter(value);
    };
    adopt(emailRef, setEmail);
    adopt(passwordRef, setPassword);
    adopt(nameRef, setName);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "register") await register(name.trim(), email.trim(), password, focusArea);
      else await login(email.trim(), password);
      router.push("/today");
      router.refresh();
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  }

  return (
    <Flex minH="100vh" bg="bg.canvas">
      {/* Brand panel */}
      <Flex
        display={{ base: "none", lg: "flex" }}
        direction="column"
        justify="space-between"
        w="46%"
        p={12}
        bgGradient="linear(165deg, #14161c 0%, #1b1f2b 55%, #2a2140 100%)"
        color="white"
        position="relative"
        overflow="hidden"
      >
        <Box position="absolute" top="-120px" right="-120px" w="420px" h="420px"
          bgGradient="radial(closest-side, rgba(109,94,252,0.35), transparent)" filter="blur(8px)" />
        <HStack spacing={3} zIndex={1}>
          <AtlasMark size={34} />
          <Box>
            <Text fontWeight={800} fontSize="lg" letterSpacing="-0.02em">CSL</Text>
            <Text fontSize="11px" letterSpacing="0.18em" color="whiteAlpha.700">
              ASK · RESEARCH · DECIDE
            </Text>
          </Box>
        </HStack>
        <VStack align="flex-start" spacing={5} zIndex={1}>
          <Heading size="lg" lineHeight={1.25} fontWeight={700} letterSpacing="-0.02em" maxW="440px">
            The business-development intelligence workspace for biopharma.
          </Heading>
          <Text color="whiteAlpha.800" fontSize="md" maxW="440px" lineHeight={1.6}>
            Graph-grounded answers, continuous competitive monitoring, and
            decision-ready briefs — every insight traceable to its source.
          </Text>
          <HStack spacing={6} pt={2} color="whiteAlpha.700" fontSize="sm">
            <VStack align="flex-start" spacing={0}><Text fontWeight={700} color="white" fontSize="lg">7</Text><Text>data sources</Text></VStack>
            <VStack align="flex-start" spacing={0}><Text fontWeight={700} color="white" fontSize="lg">24/7</Text><Text>radar monitoring</Text></VStack>
            <VStack align="flex-start" spacing={0}><Text fontWeight={700} color="white" fontSize="lg">100%</Text><Text>cited &amp; traceable</Text></VStack>
          </HStack>
        </VStack>
        <Text fontSize="xs" color="whiteAlpha.600" zIndex={1}>
          © {new Date().getFullYear()} CSL Intelligence · Internal use
        </Text>
      </Flex>

      {/* Auth form */}
      <Flex flex={1} align="center" justify="center" p={{ base: 6, md: 10 }}>
        <Box w="100%" maxW="400px">
          <HStack spacing={2.5} mb={8} display={{ base: "flex", lg: "none" }}>
            <AtlasMark size={28} />
            <Text fontWeight={800} fontSize="lg">CSL</Text>
          </HStack>
          <Heading size="lg" fontWeight={700} letterSpacing="-0.02em" mb={1.5}>
            {mode === "signin" ? "Welcome back" : "Create your account"}
          </Heading>
          <Text color="text.muted" mb={8}>
            {mode === "signin"
              ? "Sign in to your intelligence workspace."
              : "Set up access to the CSL workspace."}
          </Text>

          <form onSubmit={submit}>
            <VStack spacing={4} align="stretch">
              {mode === "register" && (
                <>
                  <FormControl isRequired>
                    <FormLabel fontSize="sm" color="text.secondary">Full name</FormLabel>
                    <Input ref={nameRef} value={name} onChange={(e) => setName(e.target.value)}
                      placeholder="Sarah Reyes" autoComplete="name" size="lg" fontSize="md" />
                  </FormControl>
                  <FormControl isRequired>
                    <FormLabel fontSize="sm" color="text.secondary">Research focus area</FormLabel>
                    <Select value={focusArea} onChange={(e) => setFocusArea(e.target.value)}
                      size="lg" fontSize="md">
                      {AREA_OPTIONS.map((a) => (
                        <option key={a.id} value={a.id}>{a.label} — {a.blurb}</option>
                      ))}
                    </Select>
                  </FormControl>
                </>
              )}
              <FormControl isRequired>
                <FormLabel fontSize="sm" color="text.secondary">Work email</FormLabel>
                <Input ref={emailRef} type="email" value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@company.com" autoComplete="email" size="lg" fontSize="md" />
              </FormControl>
              <FormControl isRequired>
                <FormLabel fontSize="sm" color="text.secondary">Password</FormLabel>
                <InputGroup size="lg">
                  <Input ref={passwordRef} type={show ? "text" : "password"} value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={mode === "register" ? "At least 8 characters" : "••••••••"}
                    autoComplete={mode === "register" ? "new-password" : "current-password"}
                    fontSize="md" />
                  <InputRightElement>
                    <IconButton aria-label={show ? "Hide" : "Show"} variant="ghost" size="sm"
                      icon={show ? <LuEyeOff /> : <LuEye />} onClick={() => setShow((s) => !s)} />
                  </InputRightElement>
                </InputGroup>
              </FormControl>

              {error && (
                <Box bg="brand.50" color="brand.700" border="1px solid" borderColor="brand.200"
                  borderRadius="10px" px={3.5} py={2.5} fontSize="sm">
                  {error}
                </Box>
              )}

              <Button type="submit" size="lg" isLoading={busy} rightIcon={<LuArrowRight />} mt={1}>
                {mode === "signin" ? "Sign in" : "Create account"}
              </Button>
            </VStack>
          </form>

          <Text mt={7} fontSize="sm" color="text.muted" textAlign="center">
            {mode === "signin" ? "New to CSL?" : "Already have an account?"}{" "}
            <Text as="button" type="button" color="accent.iris" fontWeight={600}
              onClick={() => { setMode(mode === "signin" ? "register" : "signin"); setError(null); }}>
              {mode === "signin" ? "Create an account" : "Sign in"}
            </Text>
          </Text>
        </Box>
      </Flex>
    </Flex>
  );
}
