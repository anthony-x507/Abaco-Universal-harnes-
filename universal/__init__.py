"""Universal platform — plugin-based agent factory and harness."""

from universal._version import __version__
from universal.config import Settings
from universal.core.agent import Agent
from universal.core.factory import AgentFactory
from universal.core.lifecycle import AgentLifecycle
from universal.core.platform import Universal
from universal.core.registry import AgentRegistry
from universal.session import FactorySession

__all__ = [
    "Agent",
    "AgentFactory",
    "AgentLifecycle",
    "AgentRegistry",
    "FactorySession",
    "Settings",
    "Universal",
    "__version__",
]
