"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useState } from "react";

import { Chakra } from "../../../components/Chakra";
import { IconCheck, IconFile } from "../../../components/icons";
import { container, item } from "../../../lib/motion";
import {
  type Application,
  getApplication,
  saveApplication,
  submitApplication,
} from "../../../lib/application";

export default function ApplyWorkspace() {
  const [app, setApp] = useState<Application | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [savedAt, setSavedAt] = useState<number | null>(null);

  useEffect(() => {
    fetch("/api/agent/session", { credentials: "include" })
      .catch(() => {})
      .finally(() => {
        getApplication()
          .then(setApp)
          .catch(() => setError("Couldn't load your application. Is the agent running?"));
      });
  }, []);

  const setField = (key: string, value: string) =>
    setApp((a) => (a ? { ...a, fields: { ...a.fields, [key]: value } } : a));
  const toggleDoc = (key: string) =>
    setApp((a) => (a ? { ...a, documents: { ...a.documents, [key]: !a.documents[key] } } : a));

  const save = useCallback(async () => {
    if (!app || busy) return;
    setBusy(true);
    setError(null);
    try {
      const next = await saveApplication(app.fields, app.documents);
      setApp(next);
      setSavedAt(Date.now());
    } catch {
      setError("Save failed. Try again.");
    } finally {
      setBusy(false);
    }
  }, [app, busy]);

  const submit = async () => {
    if (!app || busy) return;
    setBusy(true);
    setError(null);
    try {
      await saveApplication(app.fields, app.documents);
      setApp(await submitApplication());
    } catch {
      setError("Submit failed. Try again.");
    } finally {
      setBusy(false);
    }
  };

  if (!app) {
    return (
      <div className="m-auto flex flex-col items-center gap-4 p-10 text-center">
        <Chakra size={36} />
        {error ? <p className="text-sm text-saffron-deep">{error}</p>
               : <p className="text-sm text-muted">Loading your application…</p>}
      </div>
    );
  }

  if (app.status === "submitted") {
    return (
      <div className="mx-auto flex w-full max-w-xl flex-1 flex-col items-center px-5 py-16 text-center">
        <span className="grid size-14 place-items-center rounded-full bg-saffron/15 text-saffron">
          <IconCheck className="size-7" />
        </span>
        <h1 className="mt-6 font-display text-3xl font-semibold">Application submitted</h1>
        <p className="mt-2 text-muted">
          Reference <span className="font-mono text-cream">{app.reference}</span>
        </p>
        <p className="mt-6 max-w-md text-[11px] leading-relaxed text-muted">
          This is a demo submission (integration-ready); nothing was sent to a lender. Final
          eligibility and approval rest with the lending partner after verification.
        </p>
      </div>
    );
  }

  const required = app.schema.sections.flatMap((s) => s.fields).filter((f) => f.required);
  const missingRequired = required.filter((f) => !String(app.fields[f.key] ?? "").trim());
  const canSubmit = missingRequired.length === 0 && !busy;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-5 py-6">
      <motion.div variants={container} initial="hidden" animate="show">
        <motion.h1 variants={item} className="font-display text-3xl font-semibold">
          Your loan application
        </motion.h1>
        <motion.p variants={item} className="mt-2 text-balance text-muted">
          SARTHI pre-filled{" "}
          <span className="text-cream tabular-nums">
            {app.completeness.filled} of {app.completeness.total}
          </span>{" "}
          fields from your chats. Review every field, fill the gaps, and submit.
        </motion.p>
      </motion.div>

      {app.schema.sections.map((section) => (
        <div key={section.key} className="rounded-2xl border border-ink-3 bg-ink-2/40 p-5">
          <h2 className="font-display text-lg font-semibold">{section.title}</h2>
          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            {section.fields.map((f) => {
              const value = app.fields[f.key] ?? "";
              const fromChats = app.ai_filled.includes(f.key) && String(value).trim() !== "";
              return (
                <label key={f.key} className="block">
                  <span className="flex items-center justify-between text-sm text-muted">
                    <span>{f.label}{f.required && <span className="text-saffron-deep"> *</span>}</span>
                    <span className={`text-[10px] ${fromChats ? "text-saffron" : "text-muted"}`}>
                      {fromChats ? "from your chats" : "needs input"}
                    </span>
                  </span>
                  <input
                    type={f.type === "number" ? "number" : f.type === "date" ? "date" : "text"}
                    value={value}
                    onChange={(e) => setField(f.key, e.target.value)}
                    className="mt-1 w-full rounded-xl border border-ink-3 bg-ink-2 px-3 py-2.5 text-cream outline-none focus:border-saffron/60"
                  />
                </label>
              );
            })}
          </div>
        </div>
      ))}

      <div className="rounded-2xl border border-ink-3 bg-ink-2/40 p-5">
        <h2 className="font-display text-lg font-semibold">Documents to keep ready</h2>
        <div className="mt-3 grid gap-2 sm:grid-cols-2">
          {app.schema.documents.map((d) => (
            <button
              key={d.key}
              onClick={() => toggleDoc(d.key)}
              className="flex items-center gap-2 rounded-xl border border-ink-3 px-3 py-2.5 text-left text-sm transition-colors hover:border-saffron/40"
            >
              <span className={`grid size-5 place-items-center rounded ${app.documents[d.key] ? "bg-saffron text-ink" : "bg-ink-3 text-muted"}`}>
                {app.documents[d.key] && <IconCheck className="size-3.5" />}
              </span>
              <span className={app.documents[d.key] ? "text-cream" : "text-muted"}>{d.label}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={save}
          disabled={busy}
          className="inline-flex min-h-11 items-center gap-2 rounded-full border border-saffron/50 px-5 py-2.5 text-sm font-medium text-saffron transition-colors hover:bg-saffron/10 disabled:opacity-60"
        >
          {busy ? <Chakra rolling size={18} /> : null}
          Save draft
        </button>
        <button
          onClick={submit}
          disabled={!canSubmit}
          className="inline-flex min-h-11 items-center gap-2 rounded-full bg-saffron px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-saffron-deep disabled:cursor-not-allowed disabled:opacity-50"
        >
          <IconFile className="size-4" />
          Submit application
        </button>
        {savedAt && !busy && <span className="text-xs text-muted">Draft saved</span>}
        {missingRequired.length > 0 && (
          <span className="text-xs text-muted">{missingRequired.length} required field(s) left</span>
        )}
      </div>

      <AnimatePresence>
        {error && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            role="alert" className="text-sm text-saffron-deep">
            {error}
          </motion.p>
        )}
      </AnimatePresence>

      <p className="border-t border-ink-3 pt-4 text-[11px] leading-relaxed text-muted">
        SARTHI drafted this from your own messages — please verify every field. This is a demo
        submission (integration-ready); nothing is sent to a lender.
      </p>
    </div>
  );
}
