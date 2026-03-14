from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


TEST_ROOT = Path(tempfile.gettempdir()) / "agentgraphrag-pytest"
TEST_DB = TEST_ROOT / "agentgraphrag.db"

if TEST_ROOT.exists():
    shutil.rmtree(TEST_ROOT)
TEST_ROOT.mkdir(parents=True, exist_ok=True)

os.environ["AGENTGRAPHRAG_APP_ENV"] = "test"
os.environ["AGENTGRAPHRAG_DATA_DIR"] = str(TEST_ROOT)
os.environ["AGENTGRAPHRAG_UPLOAD_DIR"] = str(TEST_ROOT / "uploads")
os.environ["AGENTGRAPHRAG_STORE_DIR"] = str(TEST_ROOT / "store")
os.environ["AGENTGRAPHRAG_MYSQL_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
