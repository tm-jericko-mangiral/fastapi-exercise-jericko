import pytest
from fastapi.testclient import TestClient

from main import app

CUSTOMER_COUNT = 6
EXISTING_CUSTOMER_ID = 101
MISSING_CUSTOMER_ID = 999


@pytest.fixture
def client():
    return TestClient(app)


def test_health_returns_healthy_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "Healthy"


def test_customers_returns_all_customers(client):
    response = client.get("/customers")

    assert response.status_code == 200
    assert len(response.json()) == CUSTOMER_COUNT


@pytest.mark.parametrize("value_tier", ["High", "Medium", "Standard"])
def test_customers_filter_returns_only_matching_tier(client, value_tier):
    response = client.get("/customers", params={"value_tier": value_tier})

    customers = response.json()
    assert response.status_code == 200
    assert len(customers) == 2
    assert {customer["value_tier"] for customer in customers} == {value_tier}


def test_customers_filter_ignores_case(client):
    response = client.get("/customers", params={"value_tier": "high"})

    customer_ids = [customer["customer_id"] for customer in response.json()]
    assert customer_ids == [101, 102]


def test_customers_filter_with_unknown_tier_returns_empty_list(client):
    response = client.get("/customers", params={"value_tier": "Unknown"})

    assert response.status_code == 200
    assert response.json() == []


def test_customer_by_id_returns_that_customer(client):
    response = client.get(f"/customers/{EXISTING_CUSTOMER_ID}")

    assert response.status_code == 200
    assert response.json()["customer_id"] == EXISTING_CUSTOMER_ID


def test_customer_by_id_returns_404_when_missing(client):
    response = client.get(f"/customers/{MISSING_CUSTOMER_ID}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Customer not found"}


def test_customer_by_id_returns_422_for_non_integer_id(client):
    response = client.get("/customers/abc")

    assert response.status_code == 422
