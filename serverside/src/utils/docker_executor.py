import base64
from dataclasses import dataclass
import json
import logging
import tempfile
import time
from uuid import uuid4
from src.config import GITHUB_APP_ID, GITHUB_APP_PRIVATE_KEY_BASE64
from src.utils.integrations.github_integration import RepoHelper
import jwt
import requests
import subprocess
from pathlib import Path


@dataclass
class TestCoverageItem:
    coverage: float
    missing_lines: list[int]


logging.basicConfig(level=logging.INFO)

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

    def _generate_jwt(self, app_id, private_key):
        payload = {
            'iat': int(time.time()) - 60,  # Issued at time
            'exp': int(time.time()) + 600,  # JWT expiration time
            'iss': app_id
        }
        token = jwt.encode(payload, private_key, algorithm='RS256')
        return token

    def _get_installation_access_token(self, installation_id, jwt):
        headers = {
            'Authorization': f'Bearer {jwt}',
            'Accept': 'application/vnd.github.v3+json'
        }
        url = f'https://api.github.com/app/installations/{installation_id}/access_tokens'
        response = requests.post(url, headers=headers)
        return response.json()['token']

    def _clone_repository(self, repo_url: str, access_token: str, output_path: Path):
        # Modify the repo URL to include the access token
        auth_repo_url = repo_url.replace('https://', f'https://x-access-token:{access_token}@')
        cmd = f'git clone {auth_repo_url} {output_path}'
        logging.info(f'Running command: {cmd}')
        subprocess.run(cmd.split(' '))

    def _build_container(self, tag: str, repo_path: Path):
        cmd = f'docker build -f {repo_path / "Dockerfile.cf"} -t {tag} {repo_path}'
        logging.info(f'Running cmd: {cmd}')
        subprocess.run(cmd.split(' '))

    def _run_tests_and_get_coverage(self, tag: str) -> PytestOutput:
        # TODO: It's temporary fix, will think about it later.
        cmd = f'docker run -t {tag} /bin/bash -c "cd serverside && pytest --cov=. --cov-report json >/dev/null; cat coverage.json"'
        logging.info(f'Running cmd: {cmd}')
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
        output = json.loads(proc.stdout.read().decode('utf-8'))
        
        # TODO: This is temporary solution for testing.
        test_coverage = {
            f'serverside/{key}': TestCoverageItem(coverage=float(info_dict['summary']['percent_covered']), missing_lines=list(info_dict['missing_lines'])) for key, info_dict in output['files'].items()
        }

        return PytestOutput(test_coverage=test_coverage)

    def _create_files(self, repo_dir: Path, new_files: dict[str, str]):
        for file_path, contents in new_files.items():
            # TODO: This is done temporarily, will change it later to properly copy it to docker.
            with open(repo_dir / file_path, 'w') as f:
                logging.info(f'Creating new file at: {repo_dir / file_path}')
                f.write(contents)

    def execute_with_new_files(self, new_files: dict[str, str]) -> PytestOutput:
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
        APP_ID = GITHUB_APP_ID
        PRIVATE_KEY = base64.b64decode(GITHUB_APP_PRIVATE_KEY_BASE64).decode("utf-8")
        installation = self.repo_helper.get_installation_by_url(self.repo_url)

        jwt_key = self._generate_jwt(APP_ID, PRIVATE_KEY)
        access_token = self._get_installation_access_token(installation.id, jwt_key)

        with tempfile.TemporaryDirectory(dir=Path.cwd()) as repo_dir:
            logging.info(f'Created temporary directory to clone repo: {repo_dir}')
            self._clone_repository(self.repo_url, access_token, output_path=repo_dir)
            if len(new_files) > 0:
                self._create_files(Path(repo_dir), new_files)
            tag = str(uuid4()).split('-')[0]
            self._build_container(tag=tag, repo_path=Path(repo_dir))

            pytest_output = self._run_tests_and_get_coverage(tag=tag)
            return pytest_output


def main():
    docker_executor = DockerExecutor('https://github.com/CaptureFlow/captureflow-py')
    # Valid input
    pytest_output = docker_executor.execute_with_new_files({'serverside/tests/test_a.py': 'print(1)'})
    print(pytest_output.test_coverage)

    # Invalid input
    pytest_output = docker_executor.execute_with_new_files({'serverside/tests/test_a.py': 'ppprint(1)'})
    print(pytest_output.test_coverage)


if __name__ == '__main__':
    main()

