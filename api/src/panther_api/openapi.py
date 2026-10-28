"""Write the OpenAPI schema to api/openapi.json, which the frontend generates its types from.

Run it after any change to the API's contract: `uv run python -m panther_api.openapi`.
"""

import json
from pathlib import Path

from panther_api.main import create_app

SCHEMA_PATH = Path(__file__).resolve().parents[2] / "openapi.json"
REGENERATE_COMMAND = "uv run python -m panther_api.openapi"


def render() -> str:
    """The schema as committed: two-space indent, FastAPI's key order, a trailing newline."""
    return json.dumps(create_app().openapi(), indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    SCHEMA_PATH.write_text(render(), encoding="utf-8")
    print(f"Wrote {SCHEMA_PATH}")


if __name__ == "__main__":
    main()
