"""Tests para core.llm_cloud — conector LLM cloud intercambiable."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.llm_cloud import LLMCloudConfig, LLMCloudError, chat_json


class TestLLMCloudConfig:
    def test_from_env_success(self):
        with patch.dict("os.environ", {
            "LLM_CLOUD_API_KEY": "test-key-123",
            "LLM_CLOUD_BASE_URL": "https://test.api.com/v1",
            "LLM_CLOUD_MODEL": "test-model",
        }):
            cfg = LLMCloudConfig.from_env()
            assert cfg.api_key == "test-key-123"
            assert cfg.base_url == "https://test.api.com/v1"
            assert cfg.model == "test-model"

    def test_from_env_defaults(self):
        with patch.dict("os.environ", {"LLM_CLOUD_API_KEY": "key"}, clear=False):
            cfg = LLMCloudConfig.from_env()
            assert "scaleway" in cfg.base_url.lower()
            assert cfg.model == "mistral-small-3.2-24b-instruct-2506"

    def test_from_env_missing_key(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(LLMCloudError, match="LLM_CLOUD_API_KEY"):
                LLMCloudConfig.from_env()


class TestChatJson:
    def _make_response(self, content_json: dict, status: int = 200):
        import json
        mock_resp = MagicMock()
        mock_resp.status_code = status
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": json.dumps(content_json)}}],
        }
        mock_resp.text = json.dumps({"choices": [{"message": {"content": json.dumps(content_json)}}]})
        return mock_resp

    @patch("core.llm_cloud.httpx.post")
    def test_success(self, mock_post):
        expected = {"su_ref": "13/2026", "contrario": "PEREZ"}
        mock_post.return_value = self._make_response(expected)
        cfg = LLMCloudConfig(base_url="https://test.api", api_key="k", model="m")
        result = chat_json([{"role": "user", "content": "test"}], config=cfg)
        assert result == expected

    @patch("core.llm_cloud.httpx.post")
    def test_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp
        cfg = LLMCloudConfig(base_url="https://test.api", api_key="k", model="m")
        with pytest.raises(LLMCloudError, match="HTTP 500"):
            chat_json([{"role": "user", "content": "test"}], config=cfg)

    @patch("core.llm_cloud.httpx.post")
    def test_invalid_json_response(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "esto no es json"}}],
        }
        mock_post.return_value = mock_resp
        cfg = LLMCloudConfig(base_url="https://test.api", api_key="k", model="m")
        with pytest.raises(LLMCloudError, match="JSON válido"):
            chat_json([{"role": "user", "content": "test"}], config=cfg)

    @patch("core.llm_cloud.httpx.post")
    def test_timeout(self, mock_post):
        import httpx
        mock_post.side_effect = httpx.TimeoutException("timeout")
        cfg = LLMCloudConfig(base_url="https://test.api", api_key="k", model="m")
        with pytest.raises(LLMCloudError, match="Timeout"):
            chat_json([{"role": "user", "content": "test"}], config=cfg)

    @patch("core.llm_cloud.httpx.post")
    def test_json_schema_passed(self, mock_post):
        expected = {"su_ref": "13/2026"}
        mock_post.return_value = self._make_response(expected)
        cfg = LLMCloudConfig(base_url="https://test.api", api_key="k", model="m")
        schema = {"type": "object", "properties": {"su_ref": {"type": "string"}}}
        chat_json(
            [{"role": "user", "content": "test"}],
            config=cfg,
            json_schema=schema,
        )
        call_body = mock_post.call_args[1]["json"]
        assert call_body["response_format"]["type"] == "json_schema"
