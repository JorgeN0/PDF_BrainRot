import pytest
from fastapi.testclient import TestClient

from app.main import app
from tests.helpers import make_clip


@pytest.fixture
def client(tmp_settings):
    make_clip(tmp_settings.backgrounds_dir / "a.mp4")
    return TestClient(app)


def post_job(client, data=b"%PDF-1.7 fake", **form):
    fields = {"background_id": "a.mp4", "length": "30", "voice": "am_michael", **form}
    return client.post("/api/jobs", files={"pdf": ("x.pdf", data, "application/pdf")}, data=fields)


def test_voices(client):
    body = client.get("/api/voices").json()
    assert body["default"] in {v["id"] for v in body["voices"]}


def test_backgrounds_listing(client):
    [bg] = client.get("/api/backgrounds").json()
    assert bg["id"] == "a.mp4"
    assert bg["thumbnail_url"] == "/api/backgrounds/a.mp4/thumbnail"
    assert client.get(bg["thumbnail_url"]).headers["content-type"] == "image/jpeg"


def test_rejects_non_pdf(client):
    resp = post_job(client, data=b"hello")
    assert resp.status_code == 400
    assert "isn't a PDF" in resp.json()["detail"]


@pytest.mark.parametrize(
    "form, message",
    [
        ({"length": "45"}, "length"),
        ({"voice": "robot"}, "Unknown voice"),
        ({"background_id": "../../etc/passwd"}, "Unknown background"),
    ],
)
def test_rejects_bad_options(client, form, message):
    resp = post_job(client, **form)
    assert resp.status_code == 400
    assert message in resp.json()["detail"]


def test_unknown_job_is_404(client):
    assert client.get("/api/jobs/nope").status_code == 404
