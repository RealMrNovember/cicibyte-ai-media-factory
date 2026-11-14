def login(client, email="admin@example.com", password="correct horse battery"):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def csrf_headers(client):
    return {"X-CSRF-Token": client.cookies.get("mf_csrf", "")}
