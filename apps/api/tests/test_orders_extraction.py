"""
Smoke tests — order extraction endpoints.

Covers:
  1. POST /orders/extract      — text, success
  2. POST /orders/extract/image — image, success
  3. POST /orders/extract/image — persistence: source_type + screenshot_path
  4. POST /orders/extract/image — unsupported MIME → 415
  5. POST /orders/extract/image — unreadable screenshot → 422 (no silent fallback)

Setup strategy (no conftest.py):
  - In-memory SQLite via DATABASE_URL env override
  - FastAPI TestClient (httpx, already in requirements.txt)
  - order_parser_service.parse_text / parse_image mocked — no real OpenAI calls
  - Path.write_bytes mocked — no disk writes
"""

import io
import os
import pytest
from unittest.mock import MagicMock, patch

# ── Force in-memory SQLite before any app import ──────────────────────────
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.schemas.order import ParsedOrder

# ── Minimal ParsedOrder that passes all downstream validation ─────────────
_PARSED_ORDER = ParsedOrder(
    client_name="Маша",
    event_type="wedding",
    city="Санкт-Петербург",
    date_text="30 апреля",
    currency="RUB",
)

# ── Test DB setup ─────────────────────────────────────────────────────────

def _make_test_client():
    """
    Create a TestClient with an isolated in-memory SQLite DB.
    Called once per module — tests share the same DB within this file.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestingSession


client, TestingSession = _make_test_client()


def _create_project() -> str:
    """Helper: create a project via API and return its id."""
    resp = client.post("/projects", json={})
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture()
def project_id():
    return _create_project()


@pytest.fixture()
def minimal_image_bytes():
    """1×1 white PNG — valid image bytes, tiny."""
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00"
        b"\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


# ── Test 1: text endpoint — success ──────────────────────────────────────

def test_extract_text_returns_parsed_order(project_id):
    """
    POST /orders/extract with valid JSON body returns ParsedOrderResponse.
    parse_text is mocked — no real OpenAI call.
    """
    with patch(
        "app.routers.orders.order_parser_service.parse_text",
        return_value=_PARSED_ORDER,
    ):
        resp = client.post(
            "/orders/extract",
            json={"project_id": project_id, "raw_text": "Нужен фотограф на свадьбу"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["event_type"] == "wedding"
    assert data["city"] == "Санкт-Петербург"
    assert "id" in data
    assert data["project_id"] == project_id


# ── Test 2: image endpoint — success ─────────────────────────────────────

def test_extract_image_returns_parsed_order(project_id, minimal_image_bytes):
    """
    POST /orders/extract/image with valid image returns ParsedOrderResponse.
    parse_image is mocked — no real OpenAI call.
    Path.write_bytes is mocked — no disk write.
    """
    with (
        patch(
            "app.routers.orders.order_parser_service.parse_image",
            return_value=_PARSED_ORDER,
        ),
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.write_bytes"),
    ):
        resp = client.post(
            "/orders/extract/image",
            data={"project_id": project_id},
            files={"screenshot": ("order.png", io.BytesIO(minimal_image_bytes), "image/png")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["event_type"] == "wedding"
    assert data["project_id"] == project_id
    assert "id" in data


# ── Test 3: image persistence ─────────────────────────────────────────────

def test_extract_image_saves_order_input_with_screenshot_path(project_id, minimal_image_bytes):
    """
    After POST /orders/extract/image:
      - OrderInput.source_type == "screenshot"
      - OrderInput.screenshot_path is non-empty and contains orders/
    Validates that persistence layer stores screenshot metadata correctly.
    """
    from app.models.order import OrderInput

    with (
        patch(
            "app.routers.orders.order_parser_service.parse_image",
            return_value=_PARSED_ORDER,
        ),
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.write_bytes"),
    ):
        resp = client.post(
            "/orders/extract/image",
            data={"project_id": project_id},
            files={"screenshot": ("order.jpg", io.BytesIO(minimal_image_bytes), "image/jpeg")},
        )

    assert resp.status_code == 200
    order_input_id = resp.json()["order_input_id"]

    # Check DB directly
    db = TestingSession()
    try:
        record = db.get(OrderInput, order_input_id)
        assert record is not None
        assert record.source_type == "screenshot"
        assert record.screenshot_path is not None
        assert record.screenshot_path.startswith("orders/")
        assert record.screenshot_path.endswith(".jpg")
        assert record.raw_text is None
    finally:
        db.close()


# ── Test 4: unsupported MIME type → 415 ──────────────────────────────────

def test_extract_image_unsupported_mime_returns_415(project_id):
    """
    POST /orders/extract/image with application/pdf → 415 Unsupported Media Type.
    No service call should happen.
    """
    with patch(
        "app.routers.orders.order_parser_service.parse_image",
    ) as mock_parse:
        resp = client.post(
            "/orders/extract/image",
            data={"project_id": project_id},
            files={"screenshot": ("doc.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
        )

    assert resp.status_code == 415
    assert "Unsupported image type" in resp.json()["detail"]
    mock_parse.assert_not_called()


# ── Test 5: unreadable screenshot → 422, no silent fallback ──────────────

def test_extract_image_unreadable_returns_422(project_id, minimal_image_bytes):
    """
    When parse_image raises ValueError (AI returned empty/unreadable result):
      - endpoint returns 422 Unprocessable Entity
      - error message is forwarded to caller (not swallowed)
    Ensures there is no silent fallback to an empty ParsedOrder.
    """
    with (
        patch(
            "app.routers.orders.order_parser_service.parse_image",
            side_effect=ValueError(
                "Screenshot could not be read: AI returned an empty result."
            ),
        ),
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.write_bytes"),
    ):
        resp = client.post(
            "/orders/extract/image",
            data={"project_id": project_id},
            files={"screenshot": ("blurry.png", io.BytesIO(minimal_image_bytes), "image/png")},
        )

    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "Screenshot could not be read" in detail
