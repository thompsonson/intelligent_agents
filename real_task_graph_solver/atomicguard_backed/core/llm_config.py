import os
from typing import Final

# OpenRouter model slugs for LLM-based repair generation - see
# documentation/task-graph/atomicguard-variant/environment_design.md.
# BOTH SLUGS CONFIRMED against OpenRouter's live catalog in a session with
# real network access (2026-07-29): each returned a real completion via
# LLMContainerFixGenerator against typing_broken's real mypy error, so
# both are valid, resolvable models - this was previously unverifiable
# only because an earlier sandbox's network policy blocked openrouter.ai
# outright ("CONNECT tunnel failed, response 403"), not because either
# name was wrong.
#
# DEFAULT_MODEL is deepseek/deepseek-v4-flash, not gemini, because that
# live run is what actually distinguished them: deepseek's repair passed
# real mypy re-verification (AttemptOutcome.PASS) with a clean, correct
# annotation change. gemini-2.5-flash-lite produced the identical correct
# fix but wrapped it in a markdown code fence (```) that
# LLMContainerFixGenerator does not strip before writing target_path,
# turning a correct fix into a Python syntax error and a false
# AttemptOutcome.FATAL. That's a real gap in atomicguard's own
# LLMContainerFixGenerator (fence-stripping), not fixable from this repo
# - tracked here rather than silently switching the default without
# explanation.
DEEPSEEK_V4_FLASH: Final[str] = "deepseek/deepseek-v4-flash"
GEMINI_2_5_FLASH_LITE: Final[str] = "google/gemini-2.5-flash-lite"

DEFAULT_MODEL: Final[str] = DEEPSEEK_V4_FLASH

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
