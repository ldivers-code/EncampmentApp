"""Shared test fixtures — credentials loaded from environment."""
import os
import pytest

# Test credentials from env (fallback for local dev)
COMMANDER_EMAIL = os.environ.get("TEST_COMMANDER_EMAIL", "commander@test.com")
COMMANDER_PASSWORD = os.environ.get("TEST_COMMANDER_PASSWORD", "test123")
ADMIN_EMAIL = COMMANDER_EMAIL
ADMIN_PASSWORD = COMMANDER_PASSWORD
TEST_CADRE_EMAIL = os.environ.get("TEST_CADRE_EMAIL", "cadre@test.com")
TEST_CADRE_PASSWORD = os.environ.get("TEST_CADRE_PASSWORD", "test123")
PARENT_EMAIL = os.environ.get("TEST_PARENT_EMAIL", "jane.hundley@test.com")
PARENT_PASSWORD = os.environ.get("TEST_PARENT_PASSWORD", "parent123")


@pytest.fixture
def commander_creds():
    return {"email": COMMANDER_EMAIL, "password": COMMANDER_PASSWORD}


@pytest.fixture
def cadre_creds():
    return {"email": TEST_CADRE_EMAIL, "password": TEST_CADRE_PASSWORD}


@pytest.fixture
def parent_creds():
    return {"email": PARENT_EMAIL, "password": PARENT_PASSWORD}
