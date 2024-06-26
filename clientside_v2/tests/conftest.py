import subprocess
import requests
import pytest
import time

@pytest.fixture(scope="session", autouse=True)
def start_docker_compose():
    """
        All the custom instrumentations require docker contains running (e.g. postgres, redis, etc).
        Also, make sure Docker itself is running.
    """
    
    def is_jaeger_running():
        """
            Checking if docker compose is already running.
            Currently, check is simplified to just checking "jaeger" container, that runs on :16686 port
        """
        try:
            response = requests.get("http://localhost:16686")
            return response.status_code == 200
        except requests.ConnectionError:
            return False

    if is_jaeger_running():
        print("Jaeger is already running, skipping docker compose start.")
    else:
        subprocess.run(["docker", "compose", "up", "-d"], check=True)

        # Wait for Jaeger to be available
        for _ in range(10):
            if is_jaeger_running():
                print("Docker compose started successfully.")
                break
            time.sleep(2)
        else:
            print("Docker compose did not start in time")

    yield

    # OpenTelemetry exports some additional traces after test suite completes
    # To allow for that, adding a delay to make sure test container can consume it
    print("Waiting for traces to be sent...")
    time.sleep(7)
    subprocess.run(["docker", "compose", "down"], check=True)
