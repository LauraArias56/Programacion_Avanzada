"""Utilidades compartidas por los tests."""

DEFAULT_PASSWORD = "password123"


def register(
    client,
    username="tester",
    email="tester@example.com",
    password=DEFAULT_PASSWORD,
    follow_redirects=True,
):
    return client.post(
        "/auth/register",
        data={
            "username": username,
            "email": email,
            "password": password,
            "confirm": password,
        },
        follow_redirects=follow_redirects,
    )


def login(
    client,
    email="tester@example.com",
    password=DEFAULT_PASSWORD,
    follow_redirects=True,
):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=follow_redirects,
    )


def logout(client):
    return client.post("/auth/logout", follow_redirects=True)
