"""Offline regression checks for library function and template indexing."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "main_ai_canri"
if str(MODULE_DIR) not in sys.path:
    sys.path.insert(0, str(MODULE_DIR))

from Code_artifact_catalog import (  # noqa: E402
    LIBRARY_FUNCTIONS_FILE,
    LIBRARY_TEMPLATES_FILE,
    CodeArtifactCatalog,
    extract_python_documentation_callables,
)


HTML_FIXTURE = """
<html>
  <dl class="py function">
    <dt class="sig sig-object py" id="json.dumps">
      <span>json.dumps(obj, *, indent=None)</span>
    </dt>
    <dd><p>Serialize obj to JSON text.</p></dd>
  </dl>
  <dl class="py method">
    <dt class="sig sig-object py" id="json.JSONEncoder.encode">
      <span>JSONEncoder.encode(self, value)</span>
    </dt>
    <dd><p>Return a JSON string representation.</p></dd>
  </dl>
</html>
"""


def main() -> None:
    callables = extract_python_documentation_callables(
        HTML_FIXTURE,
        library="json",
        source_url="https://docs.python.org/3/library/json.html",
        retrieved_utc="2026-01-01T00:00:00+00:00",
        library_version="3.14.1",
    )
    assert len(callables) == 2, callables
    assert callables[0]["function"] == "dumps"
    assert callables[0]["library"] == "json"
    assert callables[1]["qualified_name"] == "json.JSONEncoder.encode"

    directory = ROOT / "Canri_Tests"
    functions_file = directory / ".artifact_catalog_functions_test.json"
    templates_file = directory / ".artifact_catalog_templates_test.json"
    for path in (functions_file, templates_file):
        path.unlink(missing_ok=True)
    try:
        catalog = CodeArtifactCatalog(
            functions_file,
            templates_file,
        )
        first = catalog.upsert_many(callables)
        second = catalog.upsert_many(callables)
        assert first == {"inserted": 2, "updated": 0, "unchanged": 0, "rejected": 0}
        assert second == {"inserted": 0, "updated": 0, "unchanged": 2, "rejected": 0}

        local_variant = dict(callables[0])
        local_variant["library_version"] = "3.13.9"
        local_variant["source"] = {
            "source_id": "python_local_stdlib",
            "source_name": "Installed Python standard library",
            "url": "https://docs.python.org/3/library/json.html#json.dumps",
            "trust_score": 95,
            "retrieved_utc": "2026-01-02T00:00:00+00:00",
        }
        alternate = catalog.upsert_many([local_variant])
        assert alternate["updated"] == 1

        result = catalog.search("serialize json using dumps", limit=3, language="python")
        assert result
        assert result[0]["function"]["library"] == "json"
        assert result[0]["function"]["function"] == "dumps"
        assert result[0]["template"]["call_template"]
        assert result[0]["template"]["call_template"] == "json.dumps(obj)"

        function_data = json.loads(functions_file.read_text(encoding="utf-8"))
        template_data = json.loads(templates_file.read_text(encoding="utf-8"))
        assert function_data["metadata"]["count"] == 2
        assert template_data["metadata"]["count"] == 2
        for function in function_data["functions"].values():
            assert function["library"]
            assert function["function"]
            assert function["signature"]
            assert function["source"]["url"].startswith("https://")
        dumps_record = next(
            item for item in function_data["functions"].values()
            if item["qualified_name"] == "json.dumps"
        )
        assert set(dumps_record["available_versions"]) == {"3.13.9", "3.14.1"}
        assert len(dumps_record["sources"]) == 2
    finally:
        functions_file.unlink(missing_ok=True)
        templates_file.unlink(missing_ok=True)

    production_functions = json.loads(
        LIBRARY_FUNCTIONS_FILE.read_text(encoding="utf-8")
    )["functions"]
    production_templates = json.loads(
        LIBRARY_TEMPLATES_FILE.read_text(encoding="utf-8")
    )["templates"]
    assert len(production_functions) >= 600
    assert len(production_functions) == len(production_templates)
    for template in production_templates.values():
        source = "\n".join(filter(None, [
            template.get("import_statement", ""),
            template.get("call_template", ""),
        ]))
        ast.parse(source)

    print(
        "Code artifact catalog checks passed: 18/18 "
        f"({len(production_functions)} production callables validated)"
    )


if __name__ == "__main__":
    main()
