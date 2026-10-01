"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Box,
  Button,
  Flex,
  Grid,
  HStack,
  Heading,
  Input,
  Progress,
  Text,
  VStack,
} from "@chakra-ui/react";
import { LuSparkles, LuArrowRight, LuLoaderCircle, LuFileText, LuMessageSquare } from "react-icons/lu";
import { useAuth } from "@/lib/atlas/useAuth";
import { PageContainer, SectionLabel, Card } from "@/components/atlas/ui";
import { OvernightDigest } from "@/components/atlas/OvernightDigest";
import { SinceYouLastLooked } from "@/components/atlas/SinceYouLastLooked";
import { NeedsAttention } from "@/components/atlas/NeedsAttention";
import type { StatsResponse } from "@/lib/atlas/scout";
import { useScoutData } from "@/hooks/useScout";

const QUICK = [
  "What do we know about emicizumab?",
  "Compare Sangamo and BioMarin gene-therapy programs",
  "What's new on Sangamo?",
  "Show me white space in nephrology",
];

export function TodayView() {
  const router = useRouter();
  const { user, greeting } = useAuth();
  const [ask, setAsk] = useState("");

  // Headline count comes from the scanner, not from a constant. On a genuinely quiet
  // day this reads "Nothing needs your attention", which is a real and useful answer.
  const { data: stats } = useScoutData<StatsResponse>("/api/atlas/scout/stats");
  const needsAttention = (stats?.priority_counts?.high ?? 0) + (stats?.priority_counts?.med ?? 0);

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", year: "numeric",
  });

  function submitAsk(q: string) {
    const text = q.trim();
    if (text) router.push(`/ask?q=${encodeURIComponent(text)}`);
  }

  return (
    <PageContainer>
      <Heading size="xl" fontWeight={700} letterSpacing="-0.025em" color="text.primary">
        {greeting ?? `Welcome${user ? `, ${user.name.split(" ")[0]}` : ""}`}
      </Heading>
      <Text color="text.muted" mt={1.5} fontSize="15px" data-testid="attention-summary">
        {needsAttention === 0
          ? "Nothing needs your attention"
          : `${needsAttention} thing${needsAttention === 1 ? "" : "s"} need${needsAttention === 1 ? "s" : ""} your attention`}
        {" · "}{today}
      </Text>

      <SinceYouLastLooked />

      {/* Live overnight digest — what published in your focus area since you slept */}
      <Box mt={7}>
        <OvernightDigest />
      </Box>

      <NeedsAttention />

      {/* In progress + continue */}
      <Grid mt={8} templateColumns={{ base: "1fr", lg: "1fr 1fr" }} gap={5}>
        <Box>
          <SectionLabel count="1 running">In progress</SectionLabel>
          <Card px={5} py={4}>
            <HStack justify="space-between" mb={3}>
              <HStack spacing={2}>
                <Box as={LuLoaderCircle} color="accent.iris" boxSize="16px"
                  sx={{ animation: "spin 2s linear infinite", "@keyframes spin": { to: { transform: "rotate(360deg)" } } }} />
                <Text fontSize="14px" fontWeight={600} color="text.primary">
                  Diligence — XYZ Biotech (Hemophilia A)
                </Text>
              </HStack>
            </HStack>
            <Progress value={60} size="sm" borderRadius="full" colorScheme="purple" bg="bg.subtle" />
            <HStack justify="space-between" mt={2} fontSize="12px" color="text.muted">
              <Text>60% complete</Text><Text>~12 min left</Text>
            </HStack>
          </Card>
        </Box>
        <Box>
          <SectionLabel>Continue where you left off</SectionLabel>
          <VStack align="stretch" spacing={2.5}>
            {[
              { icon: LuFileText, title: "“Emicizumab long-term safety in pediatric Hemophilia A”", meta: "PubMed PMID 38421789 · Jun 25" },
              { icon: LuMessageSquare, title: "Compare Sangamo and BioMarin gene-therapy programs", meta: "12 messages · 4 citations pinned · Jun 25" },
            ].map((r, i) => (
              <Card key={i} px={4} py={3} cursor="pointer" _hover={{ borderColor: "border.default", bg: "bg.subtle" }}
                onClick={() => router.push("/ask")}>
                <HStack spacing={3}>
                  <Box as={r.icon} color="text.muted" boxSize="16px" flexShrink={0} />
                  <Box minW={0}>
                    <Text fontSize="14px" fontWeight={500} color="text.primary" noOfLines={1}>{r.title}</Text>
                    <Text fontSize="12px" color="text.subtle" mt={0.5}>{r.meta}</Text>
                  </Box>
                </HStack>
              </Card>
            ))}
          </VStack>
        </Box>
      </Grid>

      {/* Ask CSL */}
      <Box mt={9}>
        <SectionLabel>Ask CSL</SectionLabel>
        <Flex as="form" onSubmit={(e) => { e.preventDefault(); submitAsk(ask); }}
          align="center" bg="bg.panel" border="1px solid" borderColor="border.default"
          borderRadius="12px" px={3.5} py={1.5} boxShadow="card"
          _focusWithin={{ borderColor: "iris.400", boxShadow: "focus" }}>
          <Box as={LuSparkles} color="accent.iris" boxSize="18px" mr={2.5} />
          <Input variant="unstyled" value={ask} onChange={(e) => setAsk(e.target.value)}
            placeholder='e.g. "what&apos;s new on emicizumab in the last 30 days?"' fontSize="15px" py={2} />
          <Button type="submit" size="sm" borderRadius="9px" isDisabled={!ask.trim()}
            rightIcon={<LuArrowRight size={15} />}>Ask</Button>
        </Flex>
        <HStack mt={3} spacing={2} flexWrap="wrap">
          {QUICK.map((q) => (
            <Button key={q} size="sm" variant="outline" fontWeight={500} fontSize="13px"
              color="text.secondary" borderColor="border.default" borderRadius="full"
              _hover={{ bg: "bg.hover", borderColor: "border.strong" }} onClick={() => submitAsk(q)}>
              {q}
            </Button>
          ))}
        </HStack>
      </Box>
    </PageContainer>
  );
}
