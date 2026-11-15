from datetime import UTC, datetime, timedelta

import httpx
import pytest
import respx

from mediafactory.instagram import client as ig
from mediafactory.instagram.client import InstagramError

G = ig.GRAPH


def test_caption_has_title_description_and_hashtags():
    cap = ig.build_caption({"title": "The Attic", "description": "Something lives up there.", "tags": ["horror story", "creepy", "#scary"]})
    assert cap.startswith("The Attic\n\nSomething lives up there.")
    assert "#horrorstory #creepy #scary" in cap and "#shorts" not in cap


def test_caption_respects_instagram_limits():
    cap = ig.build_caption({"title": "T", "description": "x" * 5000, "tags": [f"t{i}" for i in range(50)]})
    assert len(cap) <= ig.CAPTION_MAX and cap.count("#") <= ig.HASHTAG_MAX


@respx.mock
def test_account_info_reads_professional_account():
    respx.get(f"{G}/me").mock(return_value=httpx.Response(200, json={"user_id": "1784", "username": "cici", "account_type": "BUSINESS"}))
    info = ig.account_info("tok")
    assert info == {"user_id": "1784", "username": "cici", "account_type": "BUSINESS"}


@respx.mock
def test_personal_accounts_are_refused_with_a_clear_message():
    respx.get(f"{G}/me").mock(return_value=httpx.Response(200, json={"user_id": "1", "username": "me", "account_type": "PERSONAL"}))
    with pytest.raises(InstagramError, match="professional"):
        ig.account_info("tok")


@respx.mock
def test_bad_token_reports_instagrams_message():
    respx.get(f"{G}/me").mock(return_value=httpx.Response(400, json={"error": {"message": "Invalid OAuth access token", "code": 190}}))
    with pytest.raises(InstagramError, match="Invalid OAuth access token"):
        ig.account_info("tok")


@respx.mock
def test_refresh_returns_new_token_and_expiry():
    respx.get(ig.REFRESH_URL).mock(return_value=httpx.Response(200, json={"access_token": "new", "expires_in": 5184000}))
    token, expires = ig.refresh_token("old")
    assert token == "new"
    assert abs((expires - datetime.now(UTC)) - timedelta(days=60)) < timedelta(minutes=1)


def test_refresh_is_due_after_a_week_or_near_expiry():
    now = datetime.now(UTC)
    assert not ig.refresh_due({"refreshed_at": now.isoformat(), "expires_at": (now + timedelta(days=59)).isoformat()})
    assert ig.refresh_due({"refreshed_at": (now - timedelta(days=8)).isoformat(), "expires_at": (now + timedelta(days=52)).isoformat()})
    assert ig.refresh_due({"refreshed_at": now.isoformat(), "expires_at": (now + timedelta(days=3)).isoformat()})


@respx.mock
def test_publish_reel_uploads_the_file_waits_and_publishes(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"\x00" * 1234)
    create = respx.post(f"{G}/1784/media").mock(return_value=httpx.Response(200, json={"id": "C1", "uri": "https://rupload.facebook.com/ig-api-upload/v23.0/C1"}))
    upload = respx.post("https://rupload.facebook.com/ig-api-upload/v23.0/C1").mock(return_value=httpx.Response(200, json={"success": True}))
    status = respx.get(f"{G}/C1").mock(side_effect=[httpx.Response(200, json={"status_code": "IN_PROGRESS"}),
                                                    httpx.Response(200, json={"status_code": "FINISHED"})])  # fmt: skip
    publish = respx.post(f"{G}/1784/media_publish").mock(return_value=httpx.Response(200, json={"id": "M9"}))
    respx.get(f"{G}/M9").mock(return_value=httpx.Response(200, json={"permalink": "https://www.instagram.com/reel/abc/"}))
    waits = []
    media_id, url = ig.publish_reel("tok", "1784", video, "Caption #x", sleep=waits.append)
    assert (media_id, url) == ("M9", "https://www.instagram.com/reel/abc/")
    sent = dict(httpx.QueryParams(create.calls[0].request.content.decode()))
    assert sent["media_type"] == "REELS" and sent["upload_type"] == "resumable" and sent["caption"] == "Caption #x"
    head = upload.calls[0].request.headers
    assert head["authorization"] == "OAuth tok" and head["file_size"] == "1234" and head["offset"] == "0"
    assert len(upload.calls[0].request.content) == 1234
    assert status.call_count == 2 and waits
    assert dict(httpx.QueryParams(publish.calls[0].request.content.decode()))["creation_id"] == "C1"


@respx.mock
def test_processing_error_is_reported(tmp_path):
    video = tmp_path / "v.mp4"
    video.write_bytes(b"x")
    respx.post(f"{G}/1/media").mock(return_value=httpx.Response(200, json={"id": "C", "uri": "https://rupload.facebook.com/x/C"}))
    respx.post("https://rupload.facebook.com/x/C").mock(return_value=httpx.Response(200, json={"success": True}))
    respx.get(f"{G}/C").mock(return_value=httpx.Response(200, json={"status_code": "ERROR", "status": "Error: video too long"}))
    with pytest.raises(InstagramError, match="video too long"):
        ig.publish_reel("tok", "1", video, "c", sleep=lambda s: None)


def test_transient_errors_are_marked_for_retry():
    assert ig.InstagramError("x", transient=True).transient
    assert not ig.InstagramError("x").transient
