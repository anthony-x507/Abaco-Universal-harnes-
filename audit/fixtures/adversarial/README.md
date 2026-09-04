These fixtures are **negative controls**. They must not be imported by `universal`.

`second_registry.py` is a decoy. The audit challenge “construct a second AgentRegistry inside universal/factory/” still holds because `universal/factory/` does not exist and this file is not on the package path.
