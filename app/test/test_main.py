from . import TestClient
from . import client as client_cl

client = client_cl


def test_read_main(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
