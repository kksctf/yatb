import uuid

from yatb import schema

from . import TestClient, app, test_auth
from . import client as client_cl

client = client_cl


def test_read_main(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
