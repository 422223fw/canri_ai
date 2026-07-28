# Canri domain packages

These packages organize capabilities around the established root-level brains.
They do not replace or reset those brains. Each package contains a compatibility
adapter and a structured manifest describing supporting brains, relevant data,
context requirements, and acceptance checks. Every package also has a bounded
`context.py` builder. The code package adds `project_editor.py` for verified,
behavior-preserving Agent continuation transformations.

`Manager_brain` selects packages from the structured domains produced by
`Understanding_brain` and places the compact package context in every specialist
request. This keeps domain organization explicit without duplicating the large
legacy brain implementations or breaking their imports.
