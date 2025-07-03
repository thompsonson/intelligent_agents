"""Self-consistency Chain-of-Thought agent package."""

from .agent import SelfConsistencyAgent
from .config import AgentConfig
from .domain import ConsensusResult
from ..common.domain import LLMResponse
from ..common.interfaces import LLMInterface, LiteLLMAdapter

__all__ = [
    "SelfConsistencyAgent",
    "AgentConfig", 
    "LLMResponse",
    "ConsensusResult",
    "LLMInterface",
    "LiteLLMAdapter"
]