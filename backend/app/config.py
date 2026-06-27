"""Central configuration, loaded from backend/.env.

We resolve the .env path relative to THIS file (not the current working
directory), so the backend works no matter where the process is launched
from — a bug we hit early on with bare load_dotenv().
"""

import os
import secrets
import warnings
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")


class Settings:
    # --- NVIDIA Build (OpenAI-compatible) ---
    nvidia_api_key: str = os.getenv("NVIDIA_API_KEY", "")
    nvidia_base_url: str = os.getenv(
        "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
    )

    # --- Models ---
    # Tiered chat models for automatic routing (see router.py / agent.py).
    model_light: str = os.getenv("SARTHI_MODEL_LIGHT", "meta/llama-3.1-8b-instruct")
    model_mid: str = os.getenv(
        "SARTHI_MODEL_MID", os.getenv("SARTHI_MODEL_DEFAULT", "meta/llama-3.3-70b-instruct")
    )
    model_reasoning: str = os.getenv(
        "SARTHI_MODEL_REASONING", "nvidia/llama-3.3-nemotron-super-49b-v1.5"
    )
    # Reasoning models spend tokens "thinking"; give the answer room to land.
    reasoning_max_tokens: int = int(os.getenv("SARTHI_REASONING_MAX_TOKENS", "3072"))
    # The user-facing default tier; shown by /health.
    chat_model: str = model_mid
    # Fast/cheap model for utility tasks like fact distillation.
    utility_model: str = os.getenv("SARTHI_MODEL_UTILITY", "meta/llama-3.1-8b-instruct")
    # Embedding model for long-term memory (1024-dim, QA-retrieval tuned).
    embed_model: str = os.getenv("SARTHI_EMBED_MODEL", "nvidia/nv-embedqa-e5-v5")

    # --- DeepSeek reasoning controls ---
    thinking: bool = os.getenv("SARTHI_THINKING", "true").lower() == "true"
    reasoning_effort: str = os.getenv("SARTHI_REASONING_EFFORT", "low")

    # --- Storage paths (local dev) ---
    chroma_dir: str = str(BACKEND_DIR / "chroma_db")
    checkpoint_db: str = str(BACKEND_DIR / "sarthi_state.db")

    # --- Auth (anonymous signed-cookie identity) ---
    # Secret used to sign identity cookies. A random per-process default keeps
    # dev safe-by-accident, but set SARTHI_SECRET_KEY so identities survive
    # restarts (and are stable across instances).
    secret_key: str = os.getenv("SARTHI_SECRET_KEY", "")
    if not secret_key:
        warnings.warn(
            "SARTHI_SECRET_KEY not set — using a random per-process secret. "
            "Identity cookies will not survive a restart. Set it in .env.",
            stacklevel=2,
        )
        secret_key = secrets.token_urlsafe(48)
    # Send cookies only over HTTPS. Off in local dev (http); on in production.
    cookie_secure: bool = os.getenv("SARTHI_COOKIE_SECURE", "false").lower() == "true"

    # --- Dev flags ---
    # Debug-only endpoints (e.g. inspecting memory) are off unless explicitly
    # enabled. NEVER enable in a deployment without auth.
    debug: bool = os.getenv("SARTHI_DEBUG", "false").lower() == "true"

    def require_key(self) -> None:
        if not self.nvidia_api_key:
            raise RuntimeError(
                "NVIDIA_API_KEY is not set. Copy backend/.env.example to "
                "backend/.env and fill it in."
            )

    @property
    def chat_extra_body(self) -> dict:
        """extra_body for DeepSeek-style reasoning models. Harmless for others."""
        return {
            "chat_template_kwargs": {
                "thinking": self.thinking,
                "reasoning_effort": self.reasoning_effort,
            }
        }


settings = Settings()

# --- Domain constants (centralized; never hardcode these in logic) ---
# USD per 1 INR. Env-overridable because the rate drifts; default ≈ ₹84/USD.
USD_PER_INR: float = float(os.getenv("SARTHI_USD_PER_INR", 1 / 84))

# ROI Predictor (F3) — all tunables live here, never inline in roi.py.
ROI_DEFAULT_INTEREST_RATE: float = 10.5  # annual %, typical Indian education loan
ROI_DEFAULT_TENURE_YEARS: int = 8        # loan repayment tenure
ROI_DEFAULT_LOAN_FRACTION: float = 0.70  # fallback loan = 70% of total cost
ROI_DEFAULT_YEARS: int = 2               # degree length in years
ROI_LIST_LIMIT: int = 6                  # max universities in a base-case list
ROI_SENSITIVITY_RATES: tuple[float, ...] = (9.0, 10.5, 12.0)   # grid columns (%)
ROI_SENSITIVITY_TENURES: tuple[int, ...] = (5, 8, 10)          # grid rows (years)
ROI_PRESTIGE_BASE: float = 0.9   # salary multiplier at competitiveness 1
ROI_PRESTIGE_STEP: float = 0.05  # +per competitiveness point (→ 1.1 at comp 5)

# --- F4 SOP Co-Pilot (tunables centralized; never hardcode in logic) ---
SOP_DB_PATH: str = os.getenv("SARTHI_SOP_DB", str(BACKEND_DIR / "sarthi_sop.db"))
SOP_TARGET_WORDS_MIN: int = 700   # typical SOP lower bound
SOP_TARGET_WORDS_MAX: int = 1000  # typical SOP upper bound
SOP_LONG_SENTENCE_WORDS: int = 40  # sentences longer than this are flagged

# --- Model routing (automatic tier selection; tunables centralized) ---
# A turn is "trivial" (-> light 8B) only if it is short AND matches a pattern
# below AND is not a question. Keep this conservative: misrouting up to MID is
# safe, misrouting a real question down to the 8B is not.
ROUTER_TRIVIAL_MAX_WORDS: int = 4
ROUTER_TRIVIAL_PATTERNS: tuple[str, ...] = (
    "hi", "hello", "hey", "namaste", "thanks", "thank you", "thx", "ty",
    "ok", "okay", "cool", "great", "got it", "nice", "good morning",
    "good evening", "good night", "bye", "shukriya", "theek hai",
)
# A turn is "complex" (-> reasoning 49B) if it is long OR contains a clearly
# comparative/decision keyword. Kept narrow on purpose (reasoning is ~27s).
ROUTER_COMPLEX_MIN_WORDS: int = 40
ROUTER_COMPLEX_KEYWORDS: tuple[str, ...] = (
    "vs", "versus", "should i", "trade-off", "tradeoff", "trade off",
    "compare", "comparison", "pros and cons", "which is better",
    "better option", "worth it",
)
# Tools whose output warrants a deep-reasoning synthesis turn after they run.
ROUTER_DEEP_TOOLS: frozenset[str] = frozenset({"review_sop"})
# A light-tier reply this short, empty, or matching a refusal is "weak" and
# triggers a one-shot retry on the mid tier.
ROUTER_WEAK_REPLY_MIN_CHARS: int = 12
ROUTER_REFUSAL_PATTERNS: tuple[str, ...] = (
    "i can't", "i cannot", "i'm unable", "i am unable",
    "as an ai", "i'm sorry, but", "i am sorry, but",
)

# --- F5 Loan Eligibility + Offer (behavior tunables; policy numbers live in
# data/loan_policy.json, never here) ---
LOAN_DEFAULT_TENURE_YEARS: int = 10            # typical education-loan tenure
LOAN_STRENGTH_STRONG_EMI_PCT: float = 40.0     # EMI <= this % of income -> Strong
LOAN_STRENGTH_MODERATE_EMI_PCT: float = 60.0   # <= this -> Moderate, else Limited
LOAN_POLICY_PATH = BACKEND_DIR / "data" / "loan_policy.json"
