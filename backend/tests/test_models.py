from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.api.routes import models as models_routes
from backend.core.model_cache import missing_configured_models
from backend.tests.conftest import FakeResponse, FakeVeniceAPIClient


def test_missing_configured_models_returns_unavailable_ids() -> None:
    assert missing_configured_models(
        {"available-model"},
        {"assistant": "available-model", "benchmark judge": "retired-model"},
    ) == {"benchmark judge": "retired-model"}


def test_compatibility_mapping_forwards_type_filter() -> None:
    fake = FakeVeniceAPIClient()
    fake.queue(
        "/models/compatibility_mapping",
        [
            FakeResponse(
                json_data={
                    "data": {"gpt-compatible-id": "venice-model-id"},
                    "object": "list",
                    "type": "text",
                }
            )
        ],
    )
    app = FastAPI()
    app.include_router(models_routes.router)
    app.dependency_overrides[models_routes.get_venice_client] = lambda: fake

    response = TestClient(app).get("/models/compatibility-mapping", params={"type": "text"})

    assert response.status_code == 200
    assert response.json()["data"] == {"gpt-compatible-id": "venice-model-id"}
    assert fake.calls[0][2] == {"type": "text"}