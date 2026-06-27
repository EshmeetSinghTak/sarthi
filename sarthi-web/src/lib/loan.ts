const BASE = "/api/agent";

export type LoanInputs = {
  loan_amount_inr_lakh: number;
  co_applicant_income_inr_lakh_per_year: number;
  collateral_value_inr_lakh: number;
  country: string | null;
  tenure_years: number;
};

export type Reason = { factor: string; impact: string; detail: string };

export type LoanOffer = {
  requested_inr_lakh: number;
  eligible_inr_lakh: number;
  secured: boolean;
  collateral_value_inr_lakh: number;
  indicative_rate_low_pct: number;
  indicative_rate_high_pct: number;
  tenure_years: number;
  moratorium_months: number;
  representative_emi_inr: number;
  emi_to_income_pct: number;
  eligibility_strength: "strong" | "moderate" | "limited";
  reasons: Reason[];
  shortfall_inr_lakh: number;
  disclaimers: string[];
  policy_note: string;
};

export const getOffer = (inputs: LoanInputs) =>
  fetch(`${BASE}/loan/offer`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(inputs),
  }).then(async (res) => {
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return (await res.json()).offer as LoanOffer;
  });
