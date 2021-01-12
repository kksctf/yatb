import os
import sys
import logging
import pytest

from fastapi.testclient import TestClient

# logger.setLevel(logging.INFO)

from .. import config  # noqa
from .. import app  # noqa

# this disables real connection to db/creating db-in-file, and forces to use only in-memory db
config.DB_NAME = None


@pytest.fixture()
def client(request):
    print("Client init")
    client = TestClient(app).__enter__()

    def client_teardown():
        print("Client shutdown")
        client.__exit__()

    request.addfinalizer(client_teardown)
    return client

# from . import test_auth  # noqa
# from . import test_main  # noqa
