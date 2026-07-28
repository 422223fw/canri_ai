"""Code capability package with lazy access to the legacy brain."""

from .project_editor import ExistingProjectEditor, project_editor


def __getattr__(name):
    if name == "brain":
        from .brain import brain

        return brain
    raise AttributeError(name)


__all__ = ["ExistingProjectEditor", "brain", "project_editor"]
