from unittest.mock import MagicMock, patch

import pytest

from src.utils.integrations.github_integration import RepoHelper
from src.utils.integrations.openai_integration import OpenAIHelper

# These two classes commonly will need to be mocked


@pytest.fixture
def mock_openai_helper():
    with patch.object(OpenAIHelper, "_create_openai_client", return_value=MagicMock()):
        mock_helper = OpenAIHelper()
        mock_helper.call_chatgpt = MagicMock(return_value="Mocked GPT response")
        yield mock_helper


@pytest.fixture
def mock_repo_helper():
    with patch.object(RepoHelper, "_get_integration", return_value=MagicMock()):
        mock_helper = RepoHelper("mock://repo_url")
        mock_helper.enrich_callgraph_with_github_context = MagicMock(return_value=None)
        mock_helper.create_pull_request_with_new_function = MagicMock(return_value=None)
        yield mock_helper
