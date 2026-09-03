"""Typed errors for the Universal platform."""


class UniversalError(Exception):
    """Base error for the Universal platform."""


class ConfigError(UniversalError):
    """Missing or invalid configuration (usually environment variables)."""


class AgentNotFound(UniversalError):
    """The requested agent is not in the registry."""


class TemplateNotFound(UniversalError):
    """The requested template id is not in the catalog."""


class ProviderError(UniversalError):
    """The language-model provider failed to complete a request."""

    def __init__(self, message: str, *, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class LifecycleError(UniversalError):
    """An illegal agent state transition was requested."""


class PluginError(UniversalError):
    """A plugin failed to install, detach, or run."""


class ChannelNotFound(UniversalError):
    """The requested channel id is not in the catalog."""


class DeployError(UniversalError):
    """Packaging or deploy failed."""
