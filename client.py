import os

import requests

ENDPOINT_URL = os.environ.get("ENDPOINT_URL", "http://localhost")
ENDPOINT_PORT = os.environ.get("ENDPOINT_PORT", "8000")
BASE_URL = f"{ENDPOINT_URL}:{ENDPOINT_PORT}"


def get_endpoint(route: str):
    full_route = f"{BASE_URL}{route}"
    print(f"GET {full_route}")

    response = requests.get(full_route)
    print(response.status_code)
    print(response.json())
    return response


def main():
    get_endpoint("/health")
    get_endpoint("/customers?value_tier=High")
    get_endpoint("/customers/101")
    get_endpoint("/customers/999")
    get_endpoint("/documents")
    get_endpoint("/documents/search?q=lounge")


if __name__ == "__main__":
    main()
