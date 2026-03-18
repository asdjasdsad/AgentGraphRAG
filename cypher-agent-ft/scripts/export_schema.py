from __future__ import annotations

from pathlib import Path

from _bootstrap import ROOT
from cypher_agent_ft.common.io import dump_json
from cypher_agent_ft.schema.loader import load_schema


def main() -> None:
    schema = load_schema(ROOT / "configs" / "schema.yaml")
    dump_json(ROOT / "data" / "intermediate" / "global_schema.json", schema.model_dump(mode="json"))
    print("exported schema to data/intermediate/global_schema.json")


if __name__ == "__main__":
    main()
