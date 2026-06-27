"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { Chakra } from "../../../components/Chakra";
import { container, item } from "../../../lib/motion";

type Role = "user" | "sarthi";
type TierLabel = "fast" | "standard" | "deep";
type Message = { id: number; role: Role; content: string; tier?: TierLabel };

// Abort the stream if SARTHI sends nothing for this long (model hang / rate-limit).
const STALL_TIMEOUT_MS = 45_000;
// Deep-reasoning turns stay silent while thinking (~27s) — give them more room.
const STALL_TIMEOUT_DEEP_MS = 90_000;

const TIER_LABEL: Record<TierLabel, string> = {
  fast: "Fast",
  standard: "Standard",
  deep: "Deep thinking",
};

const STARTERS = [
  "Robotics mein MS karna hai — kahan apply karun?",
  "₹40L budget mein US ya Canada?",
  "IELTS pehle ya GRE?",
];

/** Three-dot "thinking" pulse shown before the first token arrives. */
function Thinking() {
  return (
    <span className="flex items-center gap-1 pt-2" aria-label="SARTHI is thinking">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="size-1.5 rounded-full bg-muted"
          animate={{ opacity: [0.25, 1, 0.25], y: [0, -2, 0] }}
          transition={{ repeat: Infinity, duration: 1.1, delay: i * 0.18, ease: "easeInOut" }}
        />
      ))}
    </span>
  );
}

/** Shown while the slow reasoning tier is composing (stays silent ~27s). */
function DeepThinking() {
  return (
    <span className="flex items-center gap-2 pt-2 text-sm text-muted" aria-label="SARTHI is thinking deeply">
      SARTHI is thinking deeply
      <span className="flex items-center gap-1">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="size-1.5 rounded-full bg-saffron/70"
            animate={{ opacity: [0.25, 1, 0.25] }}
            transition={{ repeat: Infinity, duration: 1.1, delay: i * 0.18, ease: "easeInOut" }}
          />
        ))}
      </span>
    </span>
  );
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streamingId, setStreamingId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const taRef = useRef<HTMLTextAreaElement>(null);
  const nextId = useRef(1);
  const reduce = useReducedMotion();

  useEffect(() => {
    fetch("/api/agent/session", { credentials: "include" }).catch(() => {});
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: reduce ? "auto" : "smooth",
    });
  }, [messages, reduce]);

  const busy = streamingId !== null;

  async function sendText(text: string) {
    if (!text.trim() || busy) return;
    setError(null);
    setInput("");
    if (taRef.current) taRef.current.style.height = "auto";

    const userMsg: Message = { id: nextId.current++, role: "user", content: text };
    const sarthiMsg: Message = { id: nextId.current++, role: "sarthi", content: "" };
    setMessages((m) => [...m, userMsg, sarthiMsg]);
    setStreamingId(sarthiMsg.id);

    const append = (token: string) =>
      setMessages((m) =>
        m.map((msg) => (msg.id === sarthiMsg.id ? { ...msg, content: msg.content + token } : msg)),
      );

    // Watchdog: if no token arrives within STALL_TIMEOUT_MS, abort and surface
    // an error instead of spinning forever. Reset on every token received.
    const controller = new AbortController();
    let timedOut = false;
    let stallWindow = STALL_TIMEOUT_MS;
    let stall: ReturnType<typeof setTimeout> | undefined;
    const resetStall = () => {
      if (stall) clearTimeout(stall);
      stall = setTimeout(() => {
        timedOut = true;
        controller.abort();
      }, stallWindow);
    };

    const setTier = (tier: TierLabel) =>
      setMessages((m) =>
        m.map((msg) => (msg.id === sarthiMsg.id ? { ...msg, tier } : msg)),
      );

    try {
      resetStall();
      const res = await fetch("/api/agent/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
        credentials: "include",
        signal: controller.signal,
      });
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        resetStall();
        buffer += decoder.decode(value, { stream: true });
        // Frames separated by a blank line; tolerate CRLF (sse-starlette uses \r\n).
        const frames = buffer.split(/\r?\n\r?\n/);
        buffer = frames.pop() ?? "";
        for (const frame of frames) {
          let event = "message";
          const dataLines: string[] = [];
          for (const line of frame.split(/\r?\n/)) {
            if (line.startsWith(":")) continue;
            if (line.startsWith("event:")) event = line.slice(6).trim();
            else if (line.startsWith("data:")) {
              let v = line.slice(5);
              if (v.startsWith(" ")) v = v.slice(1);
              dataLines.push(v);
            }
          }
          const data = dataLines.join("\n");
          if (event === "token") append(data);
          else if (event === "meta") {
            const tier = data as TierLabel;
            setTier(tier);
            if (tier === "deep") {
              stallWindow = STALL_TIMEOUT_DEEP_MS;
              resetStall();
            }
          } else if (event === "error") setError("Something went wrong. Try again.");
        }
      }
    } catch {
      setError(
        timedOut
          ? "SARTHI is taking too long to respond — the free model may be busy. Please try again."
          : "Couldn't reach SARTHI. Is the agent running?",
      );
    } finally {
      if (stall) clearTimeout(stall);
      setStreamingId(null);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendText(input);
    }
  }

  function autoGrow(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
  }

  const empty = messages.length === 0;

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      {/* Conversation */}
      <main ref={scrollRef} className="relative flex-1 overflow-y-auto">
        <div aria-hidden className="pointer-events-none absolute left-1/2 top-24 -z-0 h-72 w-72 -translate-x-1/2 rounded-full bg-saffron/15 blur-[100px]" />
        <div className="relative mx-auto w-full max-w-2xl px-5">
          {empty ? (
            <motion.div
              variants={container}
              initial="hidden"
              animate="show"
              className="flex min-h-[64vh] flex-col items-center justify-center text-center"
            >
              <motion.div variants={item} className="aura-saffron">
                <Chakra size={44} />
              </motion.div>
              <motion.h1 variants={item} className="mt-6 font-display text-4xl font-semibold leading-tight sm:text-5xl">
                Chalo, shuru karein?
              </motion.h1>
              <motion.p variants={item} className="mt-4 max-w-md text-balance text-muted">
                Tell me where you are in your journey — I&apos;ll help you find the way. English ya Hinglish, dono chalega.
              </motion.p>
              <motion.div variants={item} className="mt-8 flex flex-wrap justify-center gap-2">
                {STARTERS.map((s) => (
                  <button
                    key={s}
                    onClick={() => sendText(s)}
                    className="rounded-full border border-ink-3 bg-ink-2/60 px-3.5 py-1.5 text-sm text-cream/90 transition hover:border-saffron/50 hover:text-cream focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/60"
                  >
                    {s}
                  </button>
                ))}
              </motion.div>
            </motion.div>
          ) : (
            <ul className="space-y-6 py-6">
              <AnimatePresence initial={false}>
                {messages.map((m) =>
                  m.role === "user" ? (
                    <motion.li
                      key={m.id}
                      layout
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ type: "spring", stiffness: 320, damping: 28 }}
                      className="flex justify-end"
                    >
                      <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm border border-ink-3 bg-ink-2 px-4 py-2.5 text-cream">
                        {m.content}
                      </div>
                    </motion.li>
                  ) : (
                    <motion.li
                      key={m.id}
                      layout
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ type: "spring", stiffness: 320, damping: 28 }}
                      className="flex gap-3"
                    >
                      <Chakra rolling={streamingId === m.id} size={28} />
                      <div className="min-w-0 flex-1 pt-0.5">
                        {m.content === "" && streamingId === m.id ? (
                          m.tier === "deep" ? <DeepThinking /> : <Thinking />
                        ) : (
                          <div className="md">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                            {streamingId === m.id && <span className="caret">▍</span>}
                          </div>
                        )}
                        {m.tier && streamingId !== m.id && m.content !== "" && (
                          <div className="mt-1.5 flex items-center gap-1.5 text-[11px] text-muted">
                            <span className="size-1.5 rounded-full bg-saffron/60" />
                            {TIER_LABEL[m.tier]}
                          </div>
                        )}
                      </div>
                    </motion.li>
                  ),
                )}
              </AnimatePresence>
            </ul>
          )}
          <AnimatePresence>
            {error && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="pb-4 text-center text-sm text-saffron-deep"
                role="alert"
              >
                {error}
              </motion.p>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Composer */}
      <footer className="z-10 border-t border-ink-3 px-5 py-4">
        <div className="mx-auto flex w-full max-w-2xl items-end gap-2 rounded-2xl border border-ink-3 bg-ink-2 px-3 py-2 transition-colors focus-within:border-saffron/60">
          <textarea
            ref={taRef}
            value={input}
            onChange={autoGrow}
            onKeyDown={onKeyDown}
            rows={1}
            placeholder="Type in English or Hinglish…"
            aria-label="Message SARTHI"
            className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-cream outline-none placeholder:text-muted"
          />
          <motion.button
            onClick={() => sendText(input)}
            disabled={busy || !input.trim()}
            aria-label="Send message"
            whileTap={{ scale: 0.9 }}
            whileHover={busy || !input.trim() ? undefined : { scale: 1.06 }}
            className="grid size-9 shrink-0 place-items-center rounded-full bg-saffron text-ink transition-colors hover:bg-saffron-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/70 disabled:cursor-not-allowed disabled:opacity-40"
          >
            <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 19V5M5 12l7-7 7 7" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </motion.button>
        </div>
        <p className="mx-auto mt-2 max-w-2xl text-center text-[11px] text-muted">
          SARTHI guides; it doesn&apos;t decide. Loan and admission outcomes rest with the institution.
        </p>
      </footer>
    </div>
  );
}
