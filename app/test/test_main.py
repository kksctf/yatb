import uuid

import pytest

from .. import schema
from . import TestClient, app
from . import client as client_cl
from . import test_auth

client = client_cl


def test_read_main(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
