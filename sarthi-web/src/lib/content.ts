export type FeatureIcon = "compass" | "list" | "chart" | "pen" | "wallet" | "file";
export type Feature = {
  id: string;
  name: string;
  blurb: string;
  status: "live" | "soon";
  icon: FeatureIcon;
};

/** The six live capabilities, F1–F6. */
export const FEATURES: Feature[] = [
  { id: "f1", name: "Conversational Agent Core", blurb: "A mentor with memory that remembers your story across every session.", status: "live", icon: "compass" },
  { id: "f2", name: "University Shortlister", blurb: "Your profile in, a ranked Reach / Target / Safe list out.", status: "live", icon: "list" },
  { id: "f3", name: "ROI Predictor", blurb: "Cost vs. salary vs. EMI — see whether a degree actually pays back.", status: "live", icon: "chart" },
  { id: "f4", name: "SOP Co-Pilot", blurb: "Socratic coaching that sharpens your statement — in your own words.", status: "live", icon: "pen" },
  { id: "f5", name: "Loan Eligibility & Offer", blurb: "A personalized funding offer, built from what SARTHI already knows.", status: "live", icon: "wallet" },
  { id: "f6", name: "Document Auto-Fill", blurb: "Your loan application, filled from your conversations — not from scratch.", status: "live", icon: "file" },
];

export type Phase = { phase: string; title: string; moment: string };

/** Priya's journey with SARTHI — the four phases, plus the amplify loop. */
export const PHASES: Phase[] = [
  { phase: "Discover", title: "“Where do I even go?”", moment: "Chat in Hinglish and get a personalized timeline: IELTS → GRE → Apps → Visa." },
  { phase: "Decide", title: "“Which ten actually fit me?”", moment: "SARTHI builds your profile, then shows a shortlist with ROI for each university." },
  { phase: "Apply", title: "“Will my SOP stand out?”", moment: "Socratic coaching sharpens your statement — the words stay yours." },
  { phase: "Fund", title: "“Can I afford it?”", moment: "A personalized loan offer, auto-filled from everything SARTHI remembers." },
  { phase: "Amplify", title: "“Bring a friend.”", moment: "Share your progress and milestones — the journey compounds." },
];

/** The core differentiator: not a chatbot, an agent. */
export const AGENT_VS_CHATBOT: { chatbot: string[]; sarthi: string[] } = {
  chatbot: ["Stateless — forgets you", "Answers only", "English-only"],
  sarthi: ["Remembers you across sessions", "Takes real actions with tools", "Hinglish & vernacular"],
};
