import os
import tempfile

import pytest

# Tests use TEST_DATABASE_URL when set (CI runs against Postgres), otherwise a throwaway SQLite file.
# Must be set before app modules are imported, since the engine is created at import time.
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{tempfile.mkdtemp()}/test.db"
# API keys are left as configured (.env) so the `llm`-marked live tests can run; all other tests mock the services.

from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c
