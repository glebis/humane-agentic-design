"""Build a standalone type specimen page from a config file.

Standard library only — the skill has to run wherever the agent does.
"""


class SpecimenError(Exception):
    """A config the user has to fix. Printed without a traceback."""


__all__ = ["SpecimenError"]
