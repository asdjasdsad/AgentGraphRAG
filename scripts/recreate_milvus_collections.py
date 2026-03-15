from __future__ import annotations

import argparse

from app.core.config import get_settings
from app.core.db_milvus import milvus_store


def main() -> None:
    parser = argparse.ArgumentParser(description="Recreate Milvus collections with the project's VARCHAR primary-key schema.")
    parser.add_argument("--chunks-only", action="store_true", help="Only recreate the chunk collection.")
    args = parser.parse_args()

    settings = get_settings()
    targets = [settings.milvus_collection]
    if not args.chunks_only:
        targets.append(settings.milvus_case_collection)

    for collection_name in targets:
        milvus_store.recreate_collection(collection_name)
        print(f"recreated {collection_name}")


if __name__ == "__main__":
    main()
