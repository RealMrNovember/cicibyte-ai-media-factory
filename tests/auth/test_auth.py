from tests.auth.conftest import csrf_headers, login


def test_login_ok_sets_cookie(client, make_user):
    make_user()
    r = login(client)
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "admin@example.com"
    assert "mf_session" in client.cookies
    assert "mf_csrf" in client.cookies
    me = client.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["role"] == "admin"


def test_login_wrong_password_401(client, make_user):
    make_user()
    assert login(client, password="wrong").status_code == 401


def test_me_requires_login_401(client):
    assert client.get("/api/auth/me").status_code == 401


def test_sixth_failed_login_429(client, make_user):
    make_user()
    codes = [login(client, password="wrong").status_code for _ in range(6)]
    assert codes[:5] == [401] * 5
    assert codes[5] == 429


def test_post_without_csrf_403(client, make_user):
    make_user()
    login(client)
    assert client.post("/api/auth/logout").status_code == 403
    assert client.post("/api/auth/logout", headers=csrf_headers(client)).status_code == 200


def test_logout_ends_session(client, make_user):
    make_user()
    login(client)
    client.post("/api/auth/logout", headers=csrf_headers(client))
    assert client.get("/api/auth/me").status_code == 401


def test_editor_forbidden_on_admin_route_403(client, make_user):
    make_user(email="ed@example.com", role="editor")
    login(client, email="ed@example.com")
    assert client.get("/api/admin/ping").status_code == 403


def test_admin_allowed_on_admin_route(client, make_user):
    make_user()
    login(client)
    assert client.get("/api/admin/ping").status_code == 200


def test_inactive_user_cannot_login(client, make_user):
    user = make_user()
    user.is_active = False
    assert login(client).status_code == 401
