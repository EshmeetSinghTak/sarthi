"use client";

import { AnimatePresence, motion, MotionConfig } from "framer-motion";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import {
  type Analysis,
  type SopMeta,
  createSop,
  getSop,
  getVersion,
  listSops,
  listVersions,
  saveVersion,
} from "../../lib/sop";

type VersionMeta = { id: number; created_at: string; word_count: number };

/* ── Motion (mirrors the chat page) ───────────────────────────────────── */
const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06, delayChildren: 0.04 } },
};
const item = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 26 } },
};

/* ── SARTHI's mark: a chariot wheel (chakra). Rolls while saving. ─────── */
function Chakra({ rolling = false, size = 28 }: { rolling?: boolean; size?: number }) {
  const spokes = Array.from({ length: 8 }, (_, i) => (i * 360) / 8);
  return (
    <motion.span
      className="grid shrink-0 place-items-center rounded-full bg-saffron/12"
      style={{ width: size, height: size }}
      animate={rolling ? { rotate: 360 } : { rotate: 0 }}
      transition={rolling ? { repeat: Infinity, ease: "linear", duration: 3.5 } : { duration: 0.2 }}
      aria-hidden
    >
      <svg viewBox="0 0 24 24" style={{ width: size * 0.7, height: size * 0.7 }} className="text-saffron">
        <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="1.4" />
        <circle cx="12" cy="12" r="2.2" fill="currentColor" />
        {spokes.map((deg) => (
          <line
            key={deg}
            x1="12"
            y1="12"
            x2="12"
            y2="3.5"
            stroke="currentColor"
            strokeWidth="1"
            transform={`rotate(${deg} 12 12)`}
          />
        ))}
      </svg>
    </motion.span>
  );
}

/* ── Inline stroke icons (no emoji) ───────────────────────────────────── */
function IconCheck({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.4" aria-hidden>
      <path d="M20 6 9 17l-5-5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function IconDash({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.4" aria-hidden>
      <path d="M5 12h14" strokeLinecap="round" />
    </svg>
  );
}
function IconPlus({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden>
      <path d="M12 5v14M5 12h14" strokeLinecap="round" />
    </svg>
  );
}
function IconRestore({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <path d="M3 12a9 9 0 1 0 2.6-6.3" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M3 4v5h5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const SIGNALS: { key: keyof Analysis["structure_signals"]; label: string }[] = [
  { key: "mentions_program", label: "Names the program" },
  { key: "mentions_goal", label: "States a goal" },
  { key: "gives_reasons", label: "Gives reasons" },
];

/* ── The editorial scorecard ──────────────────────────────────────────── */
function Scorecard({ a }: { a: Analysis }) {
  const [min, max] = a.target_words;
  const onTarget = a.length_flag === "ok";
  const lengthLabel = onTarget ? "On target" : a.length_flag === "short" ? "Too short" : "Too long";
  const frac = Math.max(0, Math.min(a.word_count / max, 1));
  // Band start marker, as a fraction of the track (0..max).
  const bandStart = Math.max(0, Math.min(min / max, 1));

  return (
    <div className="rounded-2xl border border-ink-3 bg-ink-2 p-5 sm:p-6">
      {/* Hero metric */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-baseline gap-2">
            <motion.span
              key={a.word_count}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ type: "spring", stiffness: 320, damping: 28 }}
              className="font-display text-5xl font-semibold leading-none tabular-nums"
            >
              {a.word_count}
            </motion.span>
            <span className="text-sm text-muted">words</span>
          </div>
          <p className="mt-1 text-xs text-muted tabular-nums">
            target {min}–{max}
          </p>
        </div>
        {/* Quiet length pill — color + word (never color alone) */}
        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${
            onTarget ? "bg-saffron/12 text-saffron" : "bg-saffron-deep/12 text-saffron-deep"
          }`}
        >
          {onTarget ? <IconCheck className="size-3.5" /> : <IconDash className="size-3.5" />}
          {lengthLabel}
        </span>
      </div>

      {/* Meter — fills toward the band */}
      <div className="relative mt-4 h-1.5 overflow-hidden rounded-full bg-ink-3" aria-hidden>
        <motion.div
          className={`h-full origin-left rounded-full ${onTarget ? "bg-saffron" : "bg-saffron-deep"}`}
          initial={{ scaleX: 0 }}
          animate={{ scaleX: frac }}
          transition={{ type: "spring", stiffness: 120, damping: 22 }}
          style={{ width: "100%" }}
        />
        {/* band-start tick */}
        <span
          className="absolute top-0 h-full w-px bg-cream/30"
          style={{ left: `${bandStart * 100}%` }}
        />
      </div>

      {/* Structure signals */}
      <ul className="mt-5 space-y-2">
        {SIGNALS.map(({ key, label }) => {
          const present = a.structure_signals[key];
          return (
            <li key={key} className="flex items-center gap-2 text-sm">
              <span
                className={`grid size-5 place-items-center rounded-full ${
                  present ? "bg-saffron/15 text-saffron" : "bg-ink-3 text-muted"
                }`}
              >
                {present ? <IconCheck className="size-3" /> : <IconDash className="size-3" />}
              </span>
              <span className={present ? "text-cream" : "text-muted line-through"}>{label}</span>
            </li>
          );
        })}
      </ul>

      {/* Cliché chips */}
      {a.cliche_hits.length > 0 && (
        <div className="mt-5">
          <p className="text-xs text-muted">Phrases worth rewriting in your own words</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            <AnimatePresence>
              {a.cliche_hits.map((c) => (
                <motion.span
                  key={c.phrase}
                  layout
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ type: "spring", stiffness: 360, damping: 26 }}
                  className="rounded-full bg-saffron/12 px-2.5 py-1 text-xs text-saffron"
                >
                  &ldquo;{c.phrase}&rdquo;
                  {c.count > 1 && <span className="ml-1 text-saffron/70 tabular-nums">&times;{c.count}</span>}
                </motion.span>
              ))}
            </AnimatePresence>
          </div>
        </div>
      )}

      {/* Long sentences */}
      {a.long_sentences.length > 0 && (
        <div className="mt-5">
          <p className="text-xs text-muted tabular-nums">
            {a.long_sentences.length} long sentence{a.long_sentences.length > 1 ? "s" : ""} <span>(&gt;{a.long_sentence_threshold}w)</span>
          </p>
          <ul className="mt-2 space-y-1.5">
            {a.long_sentences.map((s, i) => (
              <li key={i} className="flex items-baseline gap-2 text-sm text-cream/80">
                <span className="min-w-0 flex-1 truncate">{s.text_preview}</span>
                <span className="shrink-0 text-xs text-muted tabular-nums">{s.word_count}w</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Footer caption — signals, not a grade */}
      <p className="mt-5 border-t border-ink-3 pt-4 text-[11px] leading-relaxed text-muted">{a.note}</p>
    </div>
  );
}

export default function SopWorkspace() {
  const [sops, setSops] = useState<SopMeta[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [content, setContent] = useState("");
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [versions, setVersions] = useState<VersionMeta[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshSops = useCallback(async () => {
    try {
      setSops(await listSops());
    } catch {
      setError("Couldn't load your SOPs. Is the agent running?");
    }
  }, []);

  useEffect(() => {
    fetch("/api/agent/session", { credentials: "include" })
      .catch(() => {})
      .finally(refreshSops);
  }, [refreshSops]);

  const open = useCallback(async (id: number) => {
    setActiveId(id);
    setError(null);
    setSaved(false);
    try {
      const [{ latest }, vs] = await Promise.all([getSop(id), listVersions(id)]);
      setContent(latest?.content ?? "");
      setAnalysis(latest?.analysis ?? null);
      setVersions(vs);
    } catch {
      setError("Couldn't open this SOP. Try again.");
    }
  }, []);

  async function onNew() {
    const title = window.prompt("Name this SOP (e.g. 'CMU Robotics'):")?.trim();
    if (!title) return;
    try {
      const sop = await createSop(title);
      await refreshSops();
      await open(sop.id);
    } catch {
      setError("Couldn't create the SOP. Is the agent running?");
    }
  }

  async function onSave() {
    if (activeId === null || saving) return;
    setSaving(true);
    setSaved(false);
    setError(null);
    try {
      const { analysis: a } = await saveVersion(activeId, content);
      setAnalysis(a);
      setVersions(await listVersions(activeId));
      await refreshSops();
      setSaved(true);
      window.setTimeout(() => setSaved(false), 2200);
    } catch {
      setError("Save failed. Try again.");
    } finally {
      setSaving(false);
    }
  }

  async function onRestore(vId: number) {
    if (activeId === null) return;
    try {
      const v = await getVersion(activeId, vId);
      setContent(v.content);
    } catch {
      setError("Couldn't restore that version. Try again.");
    }
  }

  const status = saving ? "Saving your draft…" : saved ? "Draft saved" : error ?? "";

  return (
    <MotionConfig reducedMotion="user">
      <div className="flex min-h-dvh flex-col">
        {/* Header — mirrors the chat header */}
        <header className="z-10 flex items-center gap-3 border-b border-ink-3 px-5 py-3 backdrop-blur">
          <Chakra size={26} />
          <div className="flex items-baseline gap-2">
            <span className="font-display text-xl font-semibold tracking-tight">SARTHI</span>
            <span className="font-deva text-lg text-saffron">सारथी</span>
            <span className="ml-1 hidden text-sm text-muted sm:inline">· SOP Workspace</span>
          </div>
          <Link
            href="/"
            className="ml-auto inline-flex min-h-11 items-center rounded-full px-3 py-2 text-sm text-muted transition-colors hover:text-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60"
          >
            ← Chat
          </Link>
        </header>

        {/* Three zones on desktop, stacked on mobile */}
        <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
          {/* Left rail — SOP switcher */}
          <aside className="shrink-0 border-b border-ink-3 p-3 lg:w-60 lg:overflow-y-auto lg:border-b-0 lg:border-r">
            <button
              onClick={onNew}
              className="mb-3 inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-saffron/50 px-3 py-2 text-sm font-medium text-saffron transition-colors hover:bg-saffron/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60"
            >
              <IconPlus className="size-4" />
              New SOP
            </button>
            <ul className="flex gap-2 overflow-x-auto pb-1 lg:flex-col lg:gap-1 lg:overflow-visible lg:pb-0">
              {sops.map((s) => (
                <li key={s.id} className="shrink-0 lg:shrink">
                  <button
                    onClick={() => open(s.id)}
                    aria-current={s.id === activeId ? "location" : undefined}
                    className={`min-h-11 w-44 rounded-xl px-3 py-2 text-left text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60 lg:w-full ${
                      s.id === activeId
                        ? "bg-ink-2 text-cream"
                        : "text-muted hover:bg-ink-2/60 hover:text-cream"
                    }`}
                  >
                    <span className="block truncate font-medium">{s.title}</span>
                    <span className="mt-0.5 block text-[11px] text-muted tabular-nums">
                      {s.word_count != null ? `${s.word_count} words` : "no draft yet"}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </aside>

          {/* Center — editor + scorecard */}
          <main className="flex min-w-0 flex-1 flex-col">
            {activeId === null ? (
              <motion.div
                variants={container}
                initial="hidden"
                animate="show"
                className="m-auto flex max-w-md flex-col items-center px-6 py-16 text-center"
              >
                <motion.div variants={item}>
                  <Chakra size={44} />
                </motion.div>
                <motion.h1 variants={item} className="mt-6 font-display text-4xl font-semibold leading-tight">
                  Your SOP, your words.
                </motion.h1>
                <motion.p variants={item} className="mt-4 text-balance text-muted">
                  Draft your Statement of Purpose here. SARTHI questions and critiques in chat — but the
                  words stay yours. She never writes it for you.
                </motion.p>
                <motion.button
                  variants={item}
                  onClick={onNew}
                  className="mt-8 inline-flex min-h-11 items-center gap-2 rounded-full bg-saffron px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-saffron-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/70"
                >
                  <IconPlus className="size-4" />
                  New SOP
                </motion.button>
              </motion.div>
            ) : (
              <motion.div
                key={activeId}
                variants={container}
                initial="hidden"
                animate="show"
                className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 px-5 py-5"
              >
                <motion.div variants={item} className="flex min-h-[40vh] flex-col lg:min-h-[44vh]">
                  <label htmlFor="sop-editor" className="sr-only">
                    Statement of Purpose draft
                  </label>
                  <textarea
                    id="sop-editor"
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    placeholder="Write your Statement of Purpose here…"
                    className="flex-1 resize-none rounded-2xl border border-ink-3 bg-ink-2 p-4 text-cream leading-relaxed outline-none transition-colors placeholder:text-muted focus:border-saffron/60 focus-visible:ring-2 focus-visible:ring-saffron/40"
                  />
                </motion.div>

                <motion.div variants={item} className="flex flex-wrap items-center gap-3">
                  <motion.button
                    onClick={onSave}
                    disabled={saving}
                    whileTap={saving ? undefined : { scale: 0.97 }}
                    className="inline-flex min-h-11 items-center gap-2 rounded-full bg-saffron px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-saffron-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/70 disabled:cursor-not-allowed disabled:opacity-60"
                  >
                    {saving ? <Chakra rolling size={18} /> : saved ? <IconCheck className="size-4" /> : null}
                    {saving ? "Saving…" : saved ? "Saved" : "Save version"}
                  </motion.button>
                  <Link
                    href="/"
                    className="inline-flex min-h-11 items-center rounded-full px-2 text-sm text-muted transition-colors hover:text-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60"
                  >
                    Ask SARTHI to review this →
                  </Link>
                  <span aria-live="polite" className="sr-only">
                    {status}
                  </span>
                </motion.div>

                <AnimatePresence>
                  {error && (
                    <motion.p
                      initial={{ opacity: 0, y: -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      role="alert"
                      className="text-sm text-saffron-deep"
                    >
                      {error}
                    </motion.p>
                  )}
                </AnimatePresence>

                <motion.div variants={item}>
                  {analysis ? (
                    <Scorecard a={analysis} />
                  ) : (
                    <div className="rounded-2xl border border-dashed border-ink-3 bg-ink-2/40 p-6 text-center text-sm text-muted">
                      Save a version to see length, structure signals, and rewrite candidates — gentle
                      prompts to reflect on, not a grade.
                    </div>
                  )}
                </motion.div>
              </motion.div>
            )}
          </main>

          {/* Right rail — version history */}
          <aside className="shrink-0 border-t border-ink-3 lg:w-60 lg:overflow-y-auto lg:border-l lg:border-t-0">
            <details open className="group p-3">
              <summary className="flex min-h-11 cursor-pointer list-none items-center justify-between rounded-lg px-2 text-xs font-medium uppercase tracking-wide text-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60">
                <span>History {versions.length > 0 && <span className="tabular-nums">({versions.length})</span>}</span>
                <svg viewBox="0 0 24 24" className="size-4 transition-transform group-open:rotate-180" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
                  <path d="m6 9 6 6 6-6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </summary>
              {versions.length === 0 ? (
                <p className="px-2 py-3 text-xs text-muted">No versions saved yet.</p>
              ) : (
                <ul className="mt-2 space-y-1">
                  {versions.map((v) => (
                    <li
                      key={v.id}
                      className="flex items-center justify-between gap-2 rounded-lg px-2 py-1.5 hover:bg-ink-2/60"
                    >
                      <span className="min-w-0">
                        <span className="block truncate text-xs text-cream/80 tabular-nums">
                          {new Date(v.created_at).toLocaleString()}
                        </span>
                        <span className="text-[11px] text-muted tabular-nums">{v.word_count} words</span>
                      </span>
                      <button
                        onClick={() => onRestore(v.id)}
                        aria-label={`Restore version from ${new Date(v.created_at).toLocaleString()}`}
                        className="inline-flex size-11 shrink-0 items-center justify-center rounded-full text-saffron transition-colors hover:bg-saffron/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60"
                      >
                        <IconRestore className="size-4" />
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </details>
          </aside>
        </div>
      </div>
    </MotionConfig>
  );
}
