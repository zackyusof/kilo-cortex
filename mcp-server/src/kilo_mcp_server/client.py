"""HTTP client for Kilo Cortex API."""

import json
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

from .config import settings
from .models import (
    ExportRequest,
    FulltextSearchRequest,
    FulltextSearchResponse,
    HealthResponse,
    HybridSearchRequest,
    HybridSearchResponse,
    MemoryCreate,
    MemoryListResponse,
    MemoryResponse,
    MemoryUpdate,
    PatternResponse,
    RulesRequest,
    RuleCreate,
    RuleResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SessionCreate,
    SessionResponse,
    StatsResponse,
    VectorSearchRequest,
    VectorSearchResponse,
)


class CortexClient:
    """Thin HTTP client wrapping all Kilo Cortex endpoints."""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or settings.api_url).rstrip("/")
        self.timeout = settings.timeout_seconds

    def _get(self, path: str, params: Optional[dict] = None) -> httpx.Response:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        with httpx.Client(timeout=self.timeout) as client:
            return client.get(url, params=params)

    def _post(self, path: str, data: dict) -> httpx.Response:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        with httpx.Client(timeout=self.timeout) as client:
            return client.post(url, json=data)

    def _put(self, path: str, data: dict) -> httpx.Response:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        with httpx.Client(timeout=self.timeout) as client:
            return client.put(url, json=data)

    def _delete(self, path: str) -> httpx.Response:
        url = urljoin(self.base_url + "/", path.lstrip("/"))
        with httpx.Client(timeout=self.timeout) as client:
            return client.delete(url)

    def _json(self, resp: httpx.Response) -> dict[str, Any]:
        return resp.json()

    # --- Health ---

    def health(self) -> dict[str, Any]:
        return self._json(self._get("/health/"))

    # --- Stats ---

    def stats(self) -> dict[str, Any]:
        return self._json(self._get("/stats/"))

    # --- Memory CRUD ---

    def memory_create(self, payload: MemoryCreate) -> MemoryResponse:
        resp = self._post("/memory/", payload.model_dump(exclude_none=True))
        resp.raise_for_status()
        return MemoryResponse(**resp.json())

    def memory_get(self, memory_id: int) -> MemoryResponse:
        resp = self._get(f"/memory/{memory_id}")
        resp.raise_for_status()
        return MemoryResponse(**resp.json())

    def memory_update(self, memory_id: int, payload: MemoryUpdate) -> MemoryResponse:
        resp = self._put(f"/memory/{memory_id}", payload.model_dump(exclude_none=True))
        resp.raise_for_status()
        return MemoryResponse(**resp.json())

    def memory_delete(self, memory_id: int) -> dict[str, Any]:
        resp = self._delete(f"/memory/{memory_id}")
        resp.raise_for_status()
        return resp.json()

    def memory_list(
        self, page: int = 1, page_size: int = 20, sector: Optional[str] = None
    ) -> MemoryListResponse:
        params = {"page": page, "page_size": page_size}
        if sector:
            params["sector"] = sector
        resp = self._get("/memory/", params=params)
        resp.raise_for_status()
        data = resp.json()
        return MemoryListResponse(
            memories=[MemoryResponse(**m) for m in data.get("memories", [])],
            total=data.get("total", 0),
            page=data.get("page", page),
            page_size=data.get("page_size", page_size),
        )

    # --- Search ---

    def search_vector(self, payload: VectorSearchRequest) -> VectorSearchResponse:
        resp = self._post("/search/vector/", payload.model_dump())
        resp.raise_for_status()
        data = resp.json()
        return VectorSearchResponse(
            results=data.get("results", []),
            query=payload.query,
            total=data.get("total", len(data.get("results", []))),
        )

    def search_fulltext(self, payload: FulltextSearchRequest) -> FulltextSearchResponse:
        resp = self._post("/search/fulltext/", payload.model_dump())
        resp.raise_for_status()
        data = resp.json()
        return FulltextSearchResponse(
            results=data.get("results", []),
            total=data.get("total", 0),
            page=data.get("page", payload.page),
            page_size=data.get("page_size", payload.page_size),
        )

    def search_hybrid(self, payload: HybridSearchRequest) -> HybridSearchResponse:
        resp = self._post("/search/hybrid/", payload.model_dump())
        resp.raise_for_status()
        data = resp.json()
        return HybridSearchResponse(
            results=data.get("results", []),
            query=payload.query,
            total=data.get("total", len(data.get("results", []))),
        )

    def search_semantic(self, payload: SemanticSearchRequest) -> SemanticSearchResponse:
        resp = self._post("/search/semantic/", payload.model_dump())
        resp.raise_for_status()
        data = resp.json()
        return SemanticSearchResponse(
            clusters=data.get("clusters", []),
            total=data.get("total", 0),
        )

    # --- Sessions ---

    def session_create(
        self, payload: Optional[SessionCreate] = None
    ) -> SessionResponse:
        data = payload.model_dump(exclude_none=True) if payload else {}
        resp = self._post("/session/", data)
        resp.raise_for_status()
        return SessionResponse(**resp.json())

    def session_get(self, session_id: str) -> SessionResponse:
        resp = self._get(f"/session/{session_id}")
        resp.raise_for_status()
        return SessionResponse(**resp.json())

    def session_list(self, page: int = 1, page_size: int = 20) -> list[dict]:
        resp = self._get("/session/", params={"page": page, "page_size": page_size})
        resp.raise_for_status()
        return resp.json().get("sessions", [])

    def session_delete(self, session_id: str) -> dict[str, Any]:
        resp = self._delete(f"/session/{session_id}")
        resp.raise_for_status()
        return resp.json()

    # --- Rules ---

    def rules_list(self, payload: Optional[RulesRequest] = None) -> list[dict]:
        params = {}
        if payload:
            params = payload.model_dump(exclude_none=True)
        resp = self._get("/rules/", params=params)
        resp.raise_for_status()
        return resp.json().get("rules", [])

    def rules_learned(self, limit: int = 50) -> list[dict]:
        resp = self._get(f"/rules/learned/?limit={limit}")
        resp.raise_for_status()
        return resp.json().get("rules", [])

    def rule_add(self, payload: RuleCreate) -> dict:
        resp = self._post("/rules/", payload.model_dump(exclude_none=True))
        resp.raise_for_status()
        return resp.json()

    # --- Patterns ---

    def patterns_list(self) -> list[dict]:
        resp = self._get("/patterns/")
        resp.raise_for_status()
        return resp.json().get("patterns", [])

    # --- Ingest / Export ---

    def ingest(self, payload: dict) -> dict:
        resp = self._post("/ingest/", payload)
        resp.raise_for_status()
        return resp.json()

    def export(self, payload: ExportRequest) -> dict:
        resp = self._post("/export/", payload.model_dump())
        resp.raise_for_status()
        return resp.json()
