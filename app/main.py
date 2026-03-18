from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api.routes_audit import router as audit_router
from app.api.routes_cases import router as cases_router
from app.api.routes_documents import router as documents_router
from app.api.routes_ingestion import router as ingestion_router
from app.api.routes_knowledge import router as knowledge_router
from app.api.routes_prompts import router as prompts_router
from app.api.routes_qa import router as qa_router
from app.api.routes_settings import router as settings_router
from app.api.routes_workspace import router as workspace_router
from app.core.config import get_settings
from app.core.db_milvus import milvus_store
from app.core.db_mysql import documents_table
from app.core.db_neo4j import graph_store
from app.core.logging import setup_logging
from app.risk.risk_rules import bootstrap_risk_rules


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()
    bootstrap_risk_rules()
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.include_router(documents_router, prefix=settings.api_prefix)
    app.include_router(ingestion_router, prefix=settings.api_prefix)
    app.include_router(qa_router, prefix=settings.api_prefix)
    app.include_router(cases_router, prefix=settings.api_prefix)
    app.include_router(audit_router, prefix=settings.api_prefix)
    app.include_router(knowledge_router, prefix=settings.api_prefix)
    app.include_router(prompts_router, prefix=settings.api_prefix)
    app.include_router(settings_router)
    app.include_router(workspace_router)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/workspace", status_code=307)

    @app.get("/health")
    def health() -> dict:
        mysql_status = documents_table.ping()
        milvus_status = milvus_store.ping()
        neo4j_status = graph_store.ping()
        all_ok = mysql_status["ok"] and milvus_status["ok"] and neo4j_status["ok"]
        return {
            "status": "ok" if all_ok else "degraded",
            "app": settings.app_name,
            "services": {
                "mysql": mysql_status,
                "milvus": milvus_status,
                "neo4j": neo4j_status,
            },
        }

    return app


app = create_app()
