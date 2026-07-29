import os
from typing import Final

# OpenRouter model slugs for LLM-based repair generation - see
# documentation/task-graph/atomicguard-variant/environment_design.md.
# NEITHER SLUG COULD BE VERIFIED against OpenRouter's live model catalog:
# this sandbox's network policy blocks openrouter.ai outright (confirmed via
# the proxy status endpoint reporting "CONNECT tunnel failed, response 403"
# for openrouter.ai and api.openai.com alike), so these are best-effort
# names, not confirmed IDs - check https://openrouter.ai/models before
# relying on either for a real run.
DEEPSEEK_V4_FLASH: Final[str] = "deepseek/deepseek-v4-flash"
GEMINI_2_5_FLASH_LITE: Final[str] = "google/gemini-2.5-flash-lite"

DEFAULT_MODEL: Final[str] = GEMINI_2_5_FLASH_LITE

OPENROUTER_PROVIDER: Final[str] = "openrouter"
OR_KEY_ENV_VAR: Final[str] = "OR_KEY"


def openrouter_api_key() -> str:
    """Read the short-term OpenRouter key from the OR_KEY environment
    variable. Raises a clear error at this system boundary if unset,
    rather than letting a bare KeyError surface from deep inside
    atomicguard's own model factory."""
    try:
        return os.environ[OR_KEY_ENV_VAR]
    except KeyError as exc:
        raise RuntimeError(
            f"{OR_KEY_ENV_VAR} is not set - export it to a real OpenRouter "
            "API key before building an LLM-backed repair Action Pair"
        ) from exc
