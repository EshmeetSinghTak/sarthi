"""Central configuration, loaded from backend/.env.

We resolve the .env path relative to THIS file (not the current working
directory), so the backend works no matter where the process is launched
from — a bug we hit early on with bare load_dotenv().
"""

import os
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
    # Chat reasoning model (user-facing turns).
    chat_model: str = os.getenv("SARTHI_MODEL_DEFAULT", "deepseek-ai/deepseek-v4-flash")
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

    # --- Dev flags ---
    # Debug-only endpoints (e.g. inspecting a user's memory) are off unless
    # explicitly enabled. NEVER enable in a deployment without auth.
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
