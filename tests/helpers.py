def login(client, email="admin@example.com", password="correct horse battery"):
    """There is no sign-in any more; kept so older tests read the same."""
    return client.get("/api/health")


def csrf_headers(client):
    return {"X-MF-Client": "1"}
