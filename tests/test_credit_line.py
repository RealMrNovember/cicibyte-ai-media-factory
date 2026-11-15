from mediafactory import credit
from mediafactory.instagram.client import CAPTION_MAX, build_caption
from mediafactory.youtube.upload import build_metadata

H = {"X-MF-Client": "1"}
SCRIPT = {"title": "Sis", "description": "Bir gece sis çöktü.", "tags": ["korku", "gizem"]}


def test_off_by_default(db):
    assert credit.enabled(db) is False and credit.line(db, "tr") is None


def test_line_follows_the_video_language(db):
    credit.set_enabled(db, True)
    assert "CiciByte AI Media Factory" in credit.line(db, "tr") and "üretildi" in credit.line(db, "tr")
    assert credit.line(db, "en").startswith("Made with")


def test_youtube_description_gets_the_line_before_hashtags():
    meta = build_metadata(SCRIPT, language="tr", privacy="public", publish_at=None, credit="Made with X — cicibyte.com")
    desc = meta["snippet"]["description"]
    assert desc.index("Made with X") < desc.index("#shorts")
    assert "Made with" not in build_metadata(SCRIPT, language="tr", privacy="public", publish_at=None)["snippet"]["description"]


def test_instagram_caption_gets_the_line_and_stays_within_limits():
    cap = build_caption(SCRIPT, credit="Made with X — cicibyte.com")
    assert "Made with X" in cap and cap.index("Made with X") < cap.index("#korku")
    long = build_caption({**SCRIPT, "description": "x" * 5000}, credit="Made with X — cicibyte.com")
    assert len(long) <= CAPTION_MAX and "Made with X" in long


def test_settings_api(client, db):
    assert client.get("/api/publish-settings", headers=H).json() == {"credit_line": False}
    r = client.put("/api/publish-settings", json={"credit_line": True}, headers=H)
    assert r.status_code == 200 and r.json() == {"credit_line": True} and credit.enabled(db)
