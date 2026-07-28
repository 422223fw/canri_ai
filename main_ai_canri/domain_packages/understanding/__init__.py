"""User-understanding capability package with lazy legacy-brain loading."""


def __getattr__(name):
    if name == "brain":
        from .brain import brain

        return brain
    raise AttributeError(name)


__all__ = ["brain"]
