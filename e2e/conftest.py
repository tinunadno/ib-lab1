import os
import sys
import tempfile
import threading

import pytest
from werkzeug.serving import make_server

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_fd, _path = tempfile.mkstemp(suffix=".db")
os.close(_fd)
os.environ["DB_PATH"] = _path
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret"
os.environ["SEED_USERNAME"] = "alice"
os.environ["SEED_PASSWORD"] = "password"

from app import app


@pytest.fixture(scope="session")
def base():
    server = make_server("127.0.0.1", 0, app)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
