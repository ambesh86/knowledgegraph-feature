"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Avatar, Box, Button, Divider, Flex, HStack, Input, Link, Select, Switch, Text, Textarea, VStack, useColorMode, useToast } from "@chakra-ui/react";
import { useAuth } from "@/lib/atlas/useAuth";
import { AREA_OPTIONS } from "@/lib/atlas/areas";
import { apiPath } from "@/lib/basePath";
import { PageContainer, PageHeader, SectionLabel, Card } from "@/components/atlas/ui";
import { ScanningSettings } from "@/components/atlas/ScanningSettings";

const SOURCES = [
  { id: "all_sources", name: "All Sources", desc: "Cascade: Eugene graph → ClinicalTrials.gov → PubMed", on: true, live: true },
  { id: "eugene", name: "Eugene Graph", desc: "Internal biomedical knowledge graph", on: true, live: true },
  { id: "pubmed", name: "PubMed", desc: "Biomedical literature (NCBI / Europe PMC)", on: true, live: true },
  { id: "trials", name: "ClinicalTrials.gov", desc: "Live trial registry", on: true, live: true },
  { id: "edgar", name: "SEC EDGAR", desc: "Corporate filings", on: false, live: false },
  { id: "patents", name: "USPTO / EPO", desc: "Patent filings & grants", on: true, live: false },
  { id: "fda", name: "FDA / EMA", desc: "Regulatory actions", on: false, live: false },
  { id: "internal", name: "Internal docs", desc: "Team briefs & decisions", on: true, live: false },
];

export function SettingsView() {
  const router = useRouter();
  const { user, logout, refresh } = useAuth();
  const { colorMode, toggleColorMode } = useColorMode();
  const toast = useToast();
  const [sources, setSources] = useState(SOURCES);
  const [savingArea, setSavingArea] = useState(false);

  // --- Backend connection (self-mint token signing secret) ---
  const [backend, setBackend] = useState<{ configured: boolean; upn: string } | null>(null);
  const [secretInput, setSecretInput] = useState("");
  const [upnInput, setUpnInput] = useState("");
  const [savingSecret, setSavingSecret] = useState(false);
  const [generatedToken, setGeneratedToken] = useState("");
  const [genLoading, setGenLoading] = useState(false);

  const LOGIN_URL = "https://internal-eugene-search-alb-616664632.us-east-1.elb.amazonaws.com/login";

  async function generateToken() {
    setGenLoading(true);
    try {
      const res = await fetch(apiPath("/api/auth/token"), { method: "POST" });
      if (!res.ok) throw new Error("mint failed");
      const data = await res.json();
      const tok = String(data.access_token ?? "");
      setGeneratedToken(tok);
      try {
        await navigator.clipboard.writeText(tok);
        toast({ title: "Token generated and copied to clipboard", status: "success", duration: 2500 });
      } catch {
        toast({ title: "Token generated — copy it from the box below", status: "info", duration: 3000 });
      }
    } catch {
      toast({ title: "Could not generate a token — connect the secret first", status: "error", duration: 4000 });
    } finally {
      setGenLoading(false);
    }
  }

  useEffect(() => {
    fetch(apiPath("/api/atlas/backend-config"))
      .then((r) => (r.ok ? r.json() : null))
      .then((s) => { if (s) { setBackend(s); setUpnInput(s.upn ?? ""); } })
      .catch(() => undefined);
  }, []);

  async function saveBackendSecret() {
    if (secretInput.trim().length < 8) {
      toast({ title: "Paste the EUGENE_CLIENT_SECRET first", status: "warning", duration: 3000 });
      return;
    }
    setSavingSecret(true);
    try {
      const res = await fetch(apiPath("/api/atlas/backend-config"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ secret: secretInput.trim(), upn: upnInput.trim() || undefined }),
      });
      if (!res.ok) throw new Error("save failed");
      const status = await res.json();
      setBackend(status);
      setSecretInput("");
      // Prove it end-to-end: mint a token now.
      const tok = await fetch(apiPath("/api/auth/token"), { method: "POST" });
      if (tok.ok) {
        toast({ title: "Connected — tokens now self-mint automatically", status: "success", duration: 4000 });
      } else {
        toast({ title: "Secret saved, but minting a token failed — double-check the value", status: "warning", duration: 5000 });
      }
    } catch {
      toast({ title: "Could not save the secret", status: "error", duration: 4000 });
    } finally {
      setSavingSecret(false);
    }
  }

  async function onLogout() { await logout(); router.push("/login"); router.refresh(); }

  async function changeArea(focusArea: string) {
    setSavingArea(true);
    try {
      const res = await fetch(apiPath("/api/atlas/auth/profile"), {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ focusArea }),
      });
      if (!res.ok) throw new Error("Update failed");
      await refresh();
      toast({ title: "Focus area updated", status: "success", duration: 2000 });
    } catch {
      toast({ title: "Could not update focus area", status: "error", duration: 3000 });
    } finally {
      setSavingArea(false);
    }
  }

  return (
    <PageContainer maxW="780px">
      <PageHeader title="Settings" subtitle="Manage your account, appearance, and intelligence sources." />

      <SectionLabel>Account</SectionLabel>
      <Card p={5} mb={8}>
        <HStack spacing={4}>
          <Avatar size="md" name={user?.name} bg="iris.500" color="white" />
          <Box flex={1}>
            <Text fontSize="16px" fontWeight={700} color="text.primary">{user?.name}</Text>
            <Text fontSize="13.5px" color="text.muted">{user?.email}</Text>
          </Box>
          <Box px={2.5} py={1} bg="bg.subtle" borderRadius="full" fontSize="12px" fontWeight={600} color="text.muted" textTransform="capitalize">
            {user?.role}
          </Box>
        </HStack>
        <Divider my={4} borderColor="border.subtle" />
        <Button variant="outline" size="sm" color="brand.500" borderColor="brand.200"
          _hover={{ bg: "brand.50" }} onClick={onLogout}>Sign out</Button>
      </Card>

      <SectionLabel>Backend connection</SectionLabel>
      <Card p={5} mb={8}>
        <Flex justify="space-between" align="center" mb={3}>
          <Box>
            <Text fontSize="14.5px" fontWeight={600} color="text.primary">Eugene token signing</Text>
            <Text fontSize="13px" color="text.muted">
              Paste the backend&apos;s <code>EUGENE_CLIENT_SECRET</code> once. The app then mints its
              own access tokens automatically — no more daily sign-in or expiry.
            </Text>
          </Box>
          <Box px={2.5} py={1} borderRadius="full" fontSize="12px" fontWeight={700}
            bg={backend?.configured ? "rgba(22,163,74,0.12)" : "bg.subtle"}
            color={backend?.configured ? "score.up" : "text.subtle"}>
            {backend?.configured ? "CONNECTED" : "NOT SET"}
          </Box>
        </Flex>
        <VStack align="stretch" spacing={3}>
          <Box>
            <Text fontSize="12.5px" fontWeight={600} color="text.muted" mb={1}>EUGENE_CLIENT_SECRET</Text>
            <Input type="password" size="md" placeholder={backend?.configured ? "•••••••• (stored — paste to replace)" : "Paste the signing secret"}
              value={secretInput} onChange={(e) => setSecretInput(e.target.value)} autoComplete="off" />
            <Text fontSize="12px" color="text.subtle" mt={1.5}>
              This is the backend&apos;s permanent token-signing key — get it from the Eugene backend team / backend config.
              Enter it once; it is not a per-user token. Do <b>not</b> paste a <code>/login</code> token here.
            </Text>
          </Box>
          <Box>
            <Text fontSize="12.5px" fontWeight={600} color="text.muted" mb={1}>Token UPN (must be in the backend allowlist)</Text>
            <Input size="md" placeholder="Rajesh.Gupta@cslbehring.com"
              value={upnInput} onChange={(e) => setUpnInput(e.target.value)} autoComplete="off" />
          </Box>
          <Flex justify="flex-end">
            <Button size="sm" colorScheme="purple" isLoading={savingSecret} onClick={() => void saveBackendSecret()}>
              {backend?.configured ? "Update secret" : "Connect"}
            </Button>
          </Flex>

          <Divider borderColor="border.subtle" />

          <Box>
            <Flex justify="space-between" align="center" gap={3} flexWrap="wrap">
              <Box flex="1 1 300px" minW={0}>
                <Text fontSize="14px" fontWeight={600} color="text.primary">Generate a backend token</Text>
                <Text fontSize="12.5px" color="text.muted">
                  The app already mints tokens automatically for chat. Use this only if you need a raw token
                  to paste into <Link href={`${LOGIN_URL.replace("/login", "")}/docs`} isExternal color="iris.500">Swagger</Link> or
                  call the API directly. Valid ~12h.
                </Text>
              </Box>
              <Button size="sm" variant="outline" isLoading={genLoading}
                isDisabled={!backend?.configured} onClick={() => void generateToken()}>
                Generate &amp; copy
              </Button>
            </Flex>
            {generatedToken && (
              <Textarea mt={2.5} value={generatedToken} isReadOnly rows={4} fontSize="11px"
                fontFamily="mono" onFocus={(e) => e.target.select()} />
            )}
            <Text fontSize="12px" color="text.subtle" mt={2}>
              Prefer a real per-user token? Sign in at{" "}
              <Link href={LOGIN_URL} isExternal color="iris.500">the backend login page</Link>{" "}
              and copy the &ldquo;EUGENE API ACCESS TOKEN&rdquo;.
            </Text>
          </Box>
        </VStack>
      </Card>

      <SectionLabel>Research focus</SectionLabel>
      <Card p={5} mb={8}>
        <Flex justify="space-between" align="center" gap={4} flexWrap="wrap">
          <Box flex="1 1 320px" minW={0}>
            <Text fontSize="14.5px" fontWeight={600} color="text.primary">Therapeutic area</Text>
            <Text fontSize="13px" color="text.muted">
              Drives your morning digest and personalized recommendations.
            </Text>
          </Box>
          <Select maxW="300px" size="md" isDisabled={savingArea}
            value={user?.focusArea ?? "hematology"}
            onChange={(e) => void changeArea(e.target.value)}>
            {AREA_OPTIONS.map((a) => (
              <option key={a.id} value={a.id}>{a.label}</option>
            ))}
          </Select>
        </Flex>
      </Card>

      <SectionLabel>Appearance</SectionLabel>
      <Card p={5} mb={8}>
        <Flex justify="space-between" align="center">
          <Box>
            <Text fontSize="14.5px" fontWeight={600} color="text.primary">Dark mode</Text>
            <Text fontSize="13px" color="text.muted">Switch between light and dark themes.</Text>
          </Box>
          <Switch isChecked={colorMode === "dark"} onChange={toggleColorMode} colorScheme="purple" size="lg" />
        </Flex>
      </Card>

      <SectionLabel count={`${sources.filter((s) => s.on).length} of ${sources.length} enabled`}>Intelligence sources</SectionLabel>
      <Card overflow="hidden">
        {sources.map((s, i) => (
          <Flex key={s.id} px={5} py={3.5} borderTop={i ? "1px solid" : "none"} borderColor="border.subtle"
            justify="space-between" align="center">
            <Box>
              <HStack spacing={2}>
                <Text fontSize="14.5px" fontWeight={600} color="text.primary">{s.name}</Text>
                {s.live ? (
                  <Box px={1.5} py={0.5} bg="rgba(22,163,74,0.12)" color="score.up" borderRadius="5px" fontSize="10px" fontWeight={700}>LIVE</Box>
                ) : (
                  <Box px={1.5} py={0.5} bg="bg.subtle" color="text.subtle" borderRadius="5px" fontSize="10px" fontWeight={700}>SOON</Box>
                )}
              </HStack>
              <Text fontSize="13px" color="text.muted">{s.desc}</Text>
            </Box>
            <Switch isChecked={s.on} isDisabled={!s.live}
              onChange={() => setSources((arr) => arr.map((x) => x.id === s.id ? { ...x, on: !x.on } : x))}
              colorScheme="purple" />
          </Flex>
        ))}
      </Card>

      {/* BD partnership scanning — the live, configurable half of this page.
          Everything above governs how questions are answered; this governs what the
          system goes looking for on its own. */}
      <Box mt={8}>
        <SectionLabel>Partnership scanning</SectionLabel>
        <ScanningSettings />
      </Box>
    </PageContainer>
  );
}
