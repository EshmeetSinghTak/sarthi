"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";

import { Chakra } from "../../../components/Chakra";
import { IconWallet } from "../../../components/icons";
import { container, item } from "../../../lib/motion";
import { type LoanInputs, type LoanOffer, getOffer } from "../../../lib/loan";

const STRENGTH: Record<LoanOffer["eligibility_strength"], { label: string; cls: string }> = {
  strong: { label: "Strong", cls: "bg-saffron/15 text-saffron" },
  moderate: { label: "Moderate", cls: "bg-saffron-deep/15 text-saffron-deep" },
  limited: { label: "Limited", cls: "bg-ink-3 text-muted" },
};

const lakh = (n: number) => `₹${n.toLocaleString("en-IN")} L`;
const inr = (n: number) => `₹${n.toLocaleString("en-IN")}`;

function Field({
  label, value, onChange, min = 0, step = 1, suffix,
}: {
  label: string; value: number; onChange: (v: number) => void;
  min?: number; step?: number; suffix?: string;
}) {
  return (
    <label className="block">
      <span className="text-sm text-muted">{label}</span>
      <div className="mt-1 flex items-center gap-2 rounded-xl border border-ink-3 bg-ink-2 px-3 focus-within:border-saffron/60">
        <input
          type="number"
          value={Number.isNaN(value) ? "" : value}
          min={min}
          step={step}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="min-w-0 flex-1 bg-transparent py-2.5 text-cream outline-none"
        />
        {suffix && <span className="shrink-0 text-xs text-muted">{suffix}</span>}
      </div>
    </label>
  );
}

function OfferCard({ offer }: { offer: LoanOffer }) {
  const s = STRENGTH[offer.eligibility_strength];
  return (
    <motion.div
      key={`${offer.eligible_inr_lakh}-${offer.tenure_years}-${offer.indicative_rate_low_pct}`}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 26 }}
      className="rounded-2xl border border-ink-3 bg-ink-2 p-5 sm:p-6"
    >
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="flex items-baseline gap-2">
            <span className="font-display text-5xl font-semibold leading-none tabular-nums">
              {lakh(offer.eligible_inr_lakh)}
            </span>
          </div>
          <p className="mt-1 text-xs text-muted">
            indicative eligibility {offer.secured ? "· secured" : "· unsecured"}
          </p>
        </div>
        <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-medium ${s.cls}`}>
          {s.label}
        </span>
      </div>

      <dl className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          ["Rate band", `${offer.indicative_rate_low_pct}–${offer.indicative_rate_high_pct}%`],
          ["EMI / month", inr(offer.representative_emi_inr)],
          ["Tenure", `${offer.tenure_years} yrs`],
          ["Moratorium", `${offer.moratorium_months} mo`],
        ].map(([k, v]) => (
          <div key={k}>
            <dt className="text-xs text-muted">{k}</dt>
            <dd className="mt-0.5 font-display text-lg tabular-nums">{v}</dd>
          </div>
        ))}
      </dl>

      {offer.shortfall_inr_lakh > 0 && (
        <p className="mt-4 text-sm text-saffron-deep">
          {lakh(offer.shortfall_inr_lakh)} short of the {lakh(offer.requested_inr_lakh)} requested.
        </p>
      )}

      <div className="mt-5">
        <p className="text-xs text-muted">Why this estimate</p>
        <ul className="mt-2 space-y-2">
          {offer.reasons.map((r, i) => (
            <li key={i} className="flex gap-2 text-sm">
              <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-saffron/60" />
              <span><span className="text-cream">{r.factor}</span> — <span className="text-muted">{r.detail}</span></span>
            </li>
          ))}
        </ul>
      </div>

      <p className="mt-5 border-t border-ink-3 pt-4 text-[11px] leading-relaxed text-muted">
        {offer.disclaimers.join(" ")}
      </p>
    </motion.div>
  );
}

export default function LoanWorkspace() {
  const [inputs, setInputs] = useState<LoanInputs>({
    loan_amount_inr_lakh: 40,
    co_applicant_income_inr_lakh_per_year: 12,
    collateral_value_inr_lakh: 0,
    country: "US",
    tenure_years: 10,
  });
  const [offer, setOffer] = useState<LoanOffer | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const debounce = useRef<ReturnType<typeof setTimeout>>(undefined);

  useEffect(() => {
    fetch("/api/agent/session", { credentials: "include" }).catch(() => {});
  }, []);

  const compute = useCallback(async (i: LoanInputs) => {
    setLoading(true);
    setError(null);
    try {
      setOffer(await getOffer(i));
    } catch {
      setError("Couldn't compute an offer. Is the agent running?");
    } finally {
      setLoading(false);
    }
  }, []);

  const set = (patch: Partial<LoanInputs>) => {
    const next = { ...inputs, ...patch };
    setInputs(next);
    if (offer) {
      // Live recompute once an offer exists, debounced.
      if (debounce.current) clearTimeout(debounce.current);
      debounce.current = setTimeout(() => compute(next), 300);
    }
  };

  const valid =
    inputs.loan_amount_inr_lakh > 0 && inputs.co_applicant_income_inr_lakh_per_year >= 0;

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-5 py-6">
      <motion.div variants={container} initial="hidden" animate="show">
        <motion.h1 variants={item} className="font-display text-3xl font-semibold">
          What could you qualify for?
        </motion.h1>
        <motion.p variants={item} className="mt-2 text-balance text-muted">
          An indicative education-loan estimate based on co-applicant income and collateral.
          SARTHI guides; the lender decides.
        </motion.p>
      </motion.div>

      <div className="grid gap-4 rounded-2xl border border-ink-3 bg-ink-2/40 p-5 sm:grid-cols-2">
        <Field label="Loan needed" value={inputs.loan_amount_inr_lakh} suffix="₹ lakh"
          onChange={(v) => set({ loan_amount_inr_lakh: v })} />
        <Field label="Co-applicant income / year" value={inputs.co_applicant_income_inr_lakh_per_year} suffix="₹ lakh"
          onChange={(v) => set({ co_applicant_income_inr_lakh_per_year: v })} />
        <Field label="Collateral value (0 if none)" value={inputs.collateral_value_inr_lakh} suffix="₹ lakh"
          onChange={(v) => set({ collateral_value_inr_lakh: v })} />
        <label className="block">
          <span className="text-sm text-muted">Destination</span>
          <select
            value={inputs.country ?? ""}
            onChange={(e) => set({ country: e.target.value || null })}
            className="mt-1 w-full rounded-xl border border-ink-3 bg-ink-2 px-3 py-2.5 text-cream outline-none focus:border-saffron/60"
          >
            <option value="US">US</option>
            <option value="Canada">Canada</option>
            <option value="">Other</option>
          </select>
        </label>
        <label className="block sm:col-span-2">
          <span className="flex items-center justify-between text-sm text-muted">
            <span>Tenure</span>
            <span className="tabular-nums text-cream">{inputs.tenure_years} years</span>
          </span>
          <input
            type="range" min={5} max={15} step={1} value={inputs.tenure_years}
            onChange={(e) => set({ tenure_years: parseInt(e.target.value, 10) })}
            className="mt-2 w-full accent-saffron"
          />
        </label>
      </div>

      <button
        onClick={() => compute(inputs)}
        disabled={!valid || loading}
        className="inline-flex min-h-11 items-center justify-center gap-2 self-start rounded-full bg-saffron px-5 py-2.5 text-sm font-medium text-ink transition-colors hover:bg-saffron-deep focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-saffron/70 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {loading ? <Chakra rolling size={18} /> : <IconWallet className="size-4" />}
        {offer ? "Recalculate" : "See my offer"}
      </button>

      <AnimatePresence>
        {error && (
          <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            role="alert" className="text-sm text-saffron-deep">
            {error}
          </motion.p>
        )}
      </AnimatePresence>

      {offer ? (
        <OfferCard offer={offer} />
      ) : (
        <div className="aura-saffron grid place-items-center rounded-2xl border border-dashed border-ink-3 bg-ink-2/40 p-10 text-center">
          <Chakra size={36} />
          <p className="mt-4 max-w-sm text-sm text-muted">
            Enter your details and SARTHI will show an indicative amount, rate band, and EMI —
            with the reasons behind it.
          </p>
        </div>
      )}
    </div>
  );
}
