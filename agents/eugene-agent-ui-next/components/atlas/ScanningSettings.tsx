"use client";

import { useEffect, useState } from "react";
import {
  Box, Button, Divider, HStack, Input, Slider, SliderFilledTrack, SliderThumb,
  SliderTrack, Spinner, Switch, Text, VStack,
} from "@chakra-ui/react";
import { LuCheck, LuRefreshCw, LuSend, LuTriangleAlert } from "react-icons/lu";
import {
  SOURCE_LABEL, factorLabel, relativeDay,
  type RunSummary, type ScanConfigView, type ScoutSource, type ScoutStatus,
} from "@/lib/atlas/scout";
import { useScoutAction, useScoutData } from "@/hooks/useScout";
import { Card, SectionLabel } from "@/components/atlas/ui";

/**
 * Settings > Scanning.
 *
 * This panel is the use case's "configurable thresholds ... enabling the BD team to
 * tune the system without developer involvement" made real. Weights, thresholds,
 * source windows and the notification target are all editable here and stored in S3;
 * none of them live in code.
 *
 * The run history below is not decoration. `source_report` per run is the audit trail
 * — it is how an analyst finds out that yesterday's briefing was thin because USPTO
 * was rate-limiting, rather than concluding the week was quiet.
 */

interface RunsPayload {
  runs: RunSummary[];
  total: number;
  status: ScoutStatus;
  degraded: boolean;
  reason?: string;
}

const WEIGHT_KEYS = [
  "area_fit", "stage_fit", "recency", "modality_fit", "corroboration", "company_context",
] as const;

function StatusDot({ ok }: { ok: boolean }) {
  return (
    <Box w="7px" h="7px" borderRadius="full" bg={ok ? "score.up" : "priority.high"} flexShrink={0} />
  );
}

export function ScanningSettings() {
  const { data: config, loading: configLoading, refetch: refetchConfig } =
    useScoutData<ScanConfigView>("/api/atlas/scout/config");
  const { data: runsData, loading: runsLoading, refetch: refetchRuns } =
    useScoutData<RunsPayload>("/api/atlas/scout/runs?limit=10");
  const { run, pending } = useScoutAction();

  const [draft, setDraft] = useState<ScanConfigView | null>(null);
  const [saved, setSaved] = useState(false);
  const [testResult, setTestResult] = useState<string | null>(null);

  useEffect(() => {
    if (config && !config.degraded) setDraft(config);
  }, [config]);

  if (configLoading || !draft) {
    return (
      <Card px={5} py={8}>
        <HStack justify="center" spacing={3}>
          <Spinner size="sm" color="accent.iris" />
          <Text fontSize="sm" color="text.muted">Loading scan configuration…</Text>
        </HStack>
      </Card>
    );
  }

  if (config?.degraded) {
    return (
      <Card px={5} py={5}>
        <HStack spacing={2.5}>
          <Box as={LuTriangleAlert} color="priority.med" boxSize="16px" />
          <Box>
            <Text fontSize="14px" fontWeight={600} color="text.secondary">
              Scanning service unavailable
            </Text>
            <Text fontSize="12.5px" color="text.muted">{config.reason}</Text>
          </Box>
        </HStack>
      </Card>
    );
  }

  const status = runsData?.status;
  const runs = runsData?.runs ?? [];

  async function save() {
    setSaved(false);
    const result = await run("/api/atlas/scout/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        weights: draft!.weights,
        thresholds: draft!.thresholds,
        sources: draft!.sources,
        notify_min_score: draft!.notify_min_score,
        min_specific_matches: draft!.min_specific_matches,
      }),
    });
    if (result) {
      setSaved(true);
      refetchConfig();
      setTimeout(() => setSaved(false), 2500);
    }
  }

  async function rescan() {
    await run("/api/atlas/scout/scan");
    refetchRuns();
  }

  async function sendTest() {
    const result = await run("/api/atlas/scout/notify-test");
    if (!result) return setTestResult("Request failed.");
    if (!result.configured) return setTestResult("No notification channel is configured.");
    setTestResult(result.delivered ? "Test notification delivered." : "Delivery failed — check the target.");
  }

  return (
    <VStack align="stretch" spacing={6}>
      {/* ── Status ─────────────────────────────────────────────────────── */}
      <Box>
        <SectionLabel>Scanner status</SectionLabel>
        <Card px={5} py={4}>
          {runsLoading || !status ? (
            <Spinner size="sm" color="accent.iris" />
          ) : (
            <VStack align="stretch" spacing={3}>
              <HStack justify="space-between" flexWrap="wrap" gap={3}>
                <HStack spacing={4} flexWrap="wrap">
                  <HStack spacing={2}>
                    <StatusDot ok={!status.degraded} />
                    <Text fontSize="13.5px" color="text.secondary">
                      {status.running ? "Scan in progress" : "Idle"}
                    </Text>
                  </HStack>
                  <Text fontSize="13px" color="text.muted" data-testid="schedule">
                    Daily at {String(status.schedule.daily_hour).padStart(2, "0")}:
                    {String(status.schedule.daily_minute).padStart(2, "0")} {status.schedule.timezone}
                  </Text>
                  <Text fontSize="13px" color="text.muted">
                    Last run {relativeDay(status.latest_run?.started_at ?? null)}
                  </Text>
                </HStack>
                <Button size="sm" variant="outline" borderColor="border.default"
                  data-testid="settings-rescan" isLoading={pending} loadingText="Scanning"
                  leftIcon={<Box as={LuRefreshCw} boxSize="13px" />} onClick={rescan}>
                  Run scan now
                </Button>
              </HStack>

              <HStack spacing={4} flexWrap="wrap">
                {Object.entries(status.sources_available).map(([source, available]) => (
                  <HStack key={source} spacing={1.5}>
                    <StatusDot ok={available} />
                    <Text fontSize="12.5px" color="text.muted">
                      {SOURCE_LABEL[source as ScoutSource] ?? source}
                      {!available && " (no API key)"}
                    </Text>
                  </HStack>
                ))}
              </HStack>
            </VStack>
          )}
        </Card>
      </Box>

      {/* ── Sources ────────────────────────────────────────────────────── */}
      <Box>
        <SectionLabel>Sources</SectionLabel>
        <Card px={5} py={2}>
          {Object.entries(draft.sources).map(([source, settings], i) => (
            <HStack key={source} justify="space-between" py={3.5}
              borderTop={i ? "1px solid" : "none"} borderColor="border.subtle">
              <Box>
                <Text fontSize="14px" fontWeight={600} color="text.primary">
                  {SOURCE_LABEL[source as ScoutSource] ?? source}
                </Text>
                <Text fontSize="12.5px" color="text.muted">
                  {settings.window_days}-day window · up to {settings.limit_per_area} per area
                </Text>
              </Box>
              <HStack spacing={4}>
                <Input size="sm" w="90px" type="number" min={1} max={3650}
                  aria-label={`${source} window days`}
                  value={settings.window_days}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      sources: {
                        ...draft.sources,
                        [source]: { ...settings, window_days: Number(e.target.value) || 1 },
                      },
                    })
                  } />
                <Switch isChecked={settings.enabled} colorScheme="purple"
                  aria-label={`Enable ${source}`}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      sources: {
                        ...draft.sources,
                        [source]: { ...settings, enabled: e.target.checked },
                      },
                    })
                  } />
              </HStack>
            </HStack>
          ))}
        </Card>
      </Box>

      {/* ── Scoring weights ────────────────────────────────────────────── */}
      <Box>
        <SectionLabel>Scoring weights</SectionLabel>
        <Card px={5} py={4}>
          <Text fontSize="12.5px" color="text.muted" mb={4}>
            Relative weight of each factor. Scores are normalised across the factors
            that apply to a given signal, so a paper is never penalised for having no
            development stage.
          </Text>
          {WEIGHT_KEYS.map((key) => (
            <HStack key={key} spacing={4} mb={3}>
              <Text fontSize="13.5px" color="text.secondary" w="150px" flexShrink={0}>
                {factorLabel(key)}
              </Text>
              <Slider min={0} max={1} step={0.05} flex={1} maxW="260px"
                aria-label={`${key} weight`}
                value={draft.weights[key] ?? 0}
                onChange={(v) => setDraft({ ...draft, weights: { ...draft.weights, [key]: v } })}>
                <SliderTrack bg="bg.subtle"><SliderFilledTrack bg="accent.iris" /></SliderTrack>
                <SliderThumb />
              </Slider>
              <Text fontSize="13px" color="text.muted" w="40px">
                {(draft.weights[key] ?? 0).toFixed(2)}
              </Text>
            </HStack>
          ))}
        </Card>
      </Box>

      {/* ── Thresholds ─────────────────────────────────────────────────── */}
      <Box>
        <SectionLabel>Priority thresholds</SectionLabel>
        <Card px={5} py={4}>
          <VStack align="stretch" spacing={4}>
            {(["high", "med"] as const).map((band) => (
              <HStack key={band} spacing={4}>
                <Text fontSize="13.5px" color="text.secondary" w="150px" flexShrink={0}>
                  {band === "high" ? "High priority at" : "Medium priority at"}
                </Text>
                <Input size="sm" w="90px" type="number" min={0} max={100}
                  aria-label={`${band} threshold`}
                  value={draft.thresholds[band]}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      thresholds: { ...draft.thresholds, [band]: Number(e.target.value) || 0 },
                    })
                  } />
                <Text fontSize="12.5px" color="text.subtle">/ 100</Text>
              </HStack>
            ))}
            <Divider borderColor="border.subtle" />
            <HStack spacing={4}>
              <Text fontSize="13.5px" color="text.secondary" w="150px" flexShrink={0}>
                Notify at or above
              </Text>
              <Input size="sm" w="90px" type="number" min={0} max={100}
                aria-label="notification threshold"
                value={draft.notify_min_score}
                onChange={(e) =>
                  setDraft({ ...draft, notify_min_score: Number(e.target.value) || 0 })
                } />
              <Button size="sm" variant="outline" borderColor="border.default"
                data-testid="send-test-notification"
                leftIcon={<Box as={LuSend} boxSize="13px" />} onClick={sendTest} isLoading={pending}>
                Send test
              </Button>
              {testResult && <Text fontSize="12.5px" color="text.muted">{testResult}</Text>}
            </HStack>
            <HStack spacing={4}>
              <Text fontSize="13.5px" color="text.secondary" w="150px" flexShrink={0}>
                Min. specific keywords
              </Text>
              <Input size="sm" w="90px" type="number" min={0} max={5}
                aria-label="minimum specific keyword matches"
                value={draft.min_specific_matches}
                onChange={(e) =>
                  setDraft({ ...draft, min_specific_matches: Number(e.target.value) || 0 })
                } />
              <Text fontSize="12.5px" color="text.subtle">
                Records matching only generic terms are dropped
              </Text>
            </HStack>
          </VStack>
        </Card>
      </Box>

      <HStack>
        <Button size="sm" onClick={save} isLoading={pending} data-testid="save-config"
          leftIcon={saved ? <Box as={LuCheck} boxSize="14px" /> : undefined}>
          {saved ? "Saved" : "Save configuration"}
        </Button>
        <Text fontSize="12.5px" color="text.subtle">
          v{draft.version}
          {draft.updated_by ? ` · last changed by ${draft.updated_by}` : ""}
        </Text>
      </HStack>

      {/* ── Run history ────────────────────────────────────────────────── */}
      <Box>
        <SectionLabel count={`${runs.length} runs`}>Recent scans</SectionLabel>
        <Card overflow="hidden">
          {runs.length === 0 ? (
            <Box px={5} py={6} textAlign="center" color="text.muted" fontSize="sm">
              No scans have run yet.
            </Box>
          ) : (
            runs.map((r, i) => (
              <Box key={r.run_id} px={5} py={3.5} borderTop={i ? "1px solid" : "none"}
                borderColor="border.subtle" data-testid="run-row">
                <HStack justify="space-between" align="flex-start" spacing={4}>
                  <Box minW={0}>
                    <HStack spacing={2}>
                      <StatusDot ok={r.status === "ok"} />
                      <Text fontSize="13.5px" fontWeight={600} color="text.primary">
                        {r.status}
                      </Text>
                      <Text fontSize="12.5px" color="text.subtle">
                        {r.trigger} · {relativeDay(r.started_at)}
                      </Text>
                    </HStack>
                    {/* The audit trail: which source failed, and why. */}
                    {r.sources?.some((s) => !s.ok) && (
                      <Text fontSize="12px" color="priority.med" mt={1}>
                        {r.sources.filter((s) => !s.ok)
                          .map((s) => `${SOURCE_LABEL[s.source] ?? s.source}: ${s.error}`)
                          .join(" · ")}
                      </Text>
                    )}
                  </Box>
                  <Text fontSize="12.5px" color="text.muted" flexShrink={0}>
                    {r.signals_kept} signals · {r.companies_scored} companies
                  </Text>
                </HStack>
              </Box>
            ))
          )}
        </Card>
      </Box>
    </VStack>
  );
}
