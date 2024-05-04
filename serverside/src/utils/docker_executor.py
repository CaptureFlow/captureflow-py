import base64
from dataclasses import dataclass
import time
from src.config import GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY_BASE64
from src.utils.integrations.github_integration import RepoHelper
import jwt
import requests
import subprocess
from pathlib import Path


@dataclass
class TestCoverageItem:
    coverage: float
    missing_lines: list[tuple[int, int]]


class PytestOutput:
    def __init__(self, test_coverage: dict[Path, TestCoverageItem]):
        self.test_coverage = test_coverage


class DockerExecutor:
    def __init__(self, repo_url):
        """
        User repo will have .captureflow['run-tests']
        """
        self.repo_url = repo_url
        self.repo_helper = RepoHelper(repo_url=self.repo_url)
        
        APP_ID = GITHUB_APP_ID
        PRIVATE_KEY = base64.b64decode(GITHUB_APP_PRIVATE_KEY_BASE64).decode("utf-8")
        installation = self.repo_helper.get_installation_by_url(self.repo_url)

        jwt_key = self.generate_jwt(APP_ID, PRIVATE_KEY)
        access_token = self.get_installation_access_token(installation.id, jwt_key)

        self.clone_repository(repo_url, access_token)

    def generate_jwt(self, app_id, private_key):
        payload = {
            'iat': int(time.time()) - 60,  # Issued at time
            'exp': int(time.time()) + 600,  # JWT expiration time
            'iss': app_id
        }
        token = jwt.encode(payload, private_key, algorithm='RS256')
        return token

    def get_installation_access_token(self, installation_id, jwt):
        headers = {
            'Authorization': f'Bearer {jwt}',
            'Accept': 'application/vnd.github.v3+json'
        }
        url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
        response = requests.post(url, headers=headers)
        print(response.json())
        return response.json()['token']

    def clone_repository(self, repo_url, access_token):
        # Modify the repo URL to include the access token
        auth_repo_url = repo_url.replace('https://', f'https://x-access-token:{access_token}@')
        subprocess.run(['git', 'clone', auth_repo_url, 'test_repo'])


    def execute_with_new_files(new_files: dict[str, str]) -> PytestOutput:
        """
        new_files: 
            {
                '/path/to/new/test_1': 'def test_blah():\n  return True',
                '/path/to/new/test_2': 'def test_blah2():\n  return True',
            }

        gh_repo.clone_repo()
        run tests from command with coverage
        return PytestOutput
        """
        pass


def main():
    DockerExecutor('https://github.com/CaptureFlow/captureflow-py')


if __name__ == '__main__':
    main()

