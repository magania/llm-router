# LLM Router - OpenAI API compatible router for multiple LLM backends
# Copyright (C) 2025
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Tests for the authentication service.
"""
import os
import pytest
from unittest.mock import patch
from app.auth_service import AuthService


class TestAuthService:
    """Test cases for AuthService."""

    def setup_method(self):
        """Set up test method."""
        self.auth_service = AuthService()

    @patch.dict(os.environ, {}, clear=True)
    def test_no_auth_keys_loaded(self):
        """Test when no authentication keys are configured."""
        auth_service = AuthService()
        assert auth_service.get_valid_keys_count() == 0
        assert not auth_service.is_valid_key("any-key")

    @patch.dict(os.environ, {"AUTH_KEY": "test-single-key"}, clear=True)
    def test_single_auth_key_loaded(self):
        """Test loading a single AUTH_KEY."""
        auth_service = AuthService()
        assert auth_service.get_valid_keys_count() == 1
        assert auth_service.is_valid_key("test-single-key")
        assert not auth_service.is_valid_key("wrong-key")

    @patch.dict(os.environ, {
        "AUTH_KEY_01": "key-01",
        "AUTH_KEY_02": "key-02", 
        "AUTH_KEY_03": "key-03"
    }, clear=True)
    def test_multiple_auth_keys_loaded(self):
        """Test loading multiple AUTH_KEY_XX keys."""
        auth_service = AuthService()
        assert auth_service.get_valid_keys_count() == 3
        assert auth_service.is_valid_key("key-01")
        assert auth_service.is_valid_key("key-02")
        assert auth_service.is_valid_key("key-03")
        assert not auth_service.is_valid_key("invalid-key")

    @patch.dict(os.environ, {
        "AUTH_KEY_01": "key-01",
        "AUTH_KEY_03": "key-03"  # Salto en secuencia (falta 02)
    }, clear=True)
    def test_auth_keys_with_gap(self):
        """Test que el sistema se detiene en el primer salto de secuencia."""
        auth_service = AuthService()
        assert auth_service.get_valid_keys_count() == 1  # Solo debe cargar key-01
        assert auth_service.is_valid_key("key-01")
        assert not auth_service.is_valid_key("key-03")  # No debe cargar key-03

    @patch.dict(os.environ, {"AUTH_KEY": "primary-key"}, clear=True)
    def test_auth_key_priority_over_numbered(self):
        """Test que AUTH_KEY tiene prioridad sobre AUTH_KEY_XX."""
        # Agregar claves numeradas que deberían ser ignoradas
        os.environ["AUTH_KEY_01"] = "numbered-key-01"
        os.environ["AUTH_KEY_02"] = "numbered-key-02"
        
        auth_service = AuthService()
        assert auth_service.get_valid_keys_count() == 1
        assert auth_service.is_valid_key("primary-key")
        assert not auth_service.is_valid_key("numbered-key-01")
        assert not auth_service.is_valid_key("numbered-key-02")

    def test_bearer_token_handling(self):
        """Test que maneja correctamente tokens Bearer."""
        with patch.dict(os.environ, {"AUTH_KEY": "test-key"}, clear=True):
            auth_service = AuthService()
            assert auth_service.is_valid_key("Bearer test-key")
            assert auth_service.is_valid_key("test-key")
            assert not auth_service.is_valid_key("Bearer wrong-key")

    def test_empty_key_validation(self):
        """Test validación de claves vacías."""
        with patch.dict(os.environ, {"AUTH_KEY": "test-key"}, clear=True):
            auth_service = AuthService()
            assert not auth_service.is_valid_key("")
            assert not auth_service.is_valid_key(None)

    def test_key_whitespace_handling(self):
        """Test que maneja correctamente espacios en blanco."""
        with patch.dict(os.environ, {"AUTH_KEY": "  test-key  "}, clear=True):
            auth_service = AuthService()
            assert auth_service.is_valid_key("test-key")
            assert auth_service.is_valid_key("  test-key  ")

    def test_reload_keys(self):
        """Test recarga de claves desde variables de entorno."""
        with patch.dict(os.environ, {"AUTH_KEY": "original-key"}, clear=True):
            auth_service = AuthService()
            assert auth_service.is_valid_key("original-key")
            
            # Cambiar variable de entorno
            os.environ["AUTH_KEY"] = "new-key"
            auth_service.reload_keys()
            
            assert auth_service.is_valid_key("new-key")
            assert not auth_service.is_valid_key("original-key")

    def test_request_metrics_recording(self):
        """Test grabación de métricas de requests."""
        with patch.dict(os.environ, {"AUTH_KEY": "test-key"}, clear=True):
            auth_service = AuthService()
            
            # Grabar algunas requests
            auth_service.record_request("test-key", success=True)
            auth_service.record_request("test-key", success=True)
            auth_service.record_request("test-key", success=False)
            
            metrics = auth_service.get_metrics()
            assert metrics["total_requests"] == 3
            assert metrics["total_success"] == 2
            assert metrics["total_errors"] == 1
            assert metrics["success_rate"] == pytest.approx(66.67, abs=0.1)

    def test_request_metrics_bearer_token(self):
        """Test métricas con Bearer tokens."""
        with patch.dict(os.environ, {"AUTH_KEY": "test-key"}, clear=True):
            auth_service = AuthService()
            
            auth_service.record_request("Bearer test-key", success=True)
            auth_service.record_request("test-key", success=True)
            
            metrics = auth_service.get_metrics()
            assert metrics["total_requests"] == 2
            assert len(metrics["keys_metrics"]) == 1  # Ambas deben contarse para la misma clave

    def test_get_key_metrics(self):
        """Test obtener métricas de una clave específica."""
        with patch.dict(os.environ, {"AUTH_KEY": "test-key"}, clear=True):
            auth_service = AuthService()
            
            auth_service.record_request("test-key", success=True)
            auth_service.record_request("test-key", success=False)
            
            key_metrics = auth_service.get_key_metrics("test-key")
            assert key_metrics is not None
            assert key_metrics["requests_count"] == 2
            assert key_metrics["success_count"] == 1
            assert key_metrics["error_count"] == 1
            assert key_metrics["success_rate"] == 50.0

    def test_reset_metrics(self):
        """Test reseteo de métricas."""
        with patch.dict(os.environ, {"AUTH_KEY": "test-key"}, clear=True):
            auth_service = AuthService()
            
            auth_service.record_request("test-key", success=True)
            metrics_before = auth_service.get_metrics()
            assert metrics_before["total_requests"] == 1
            
            auth_service.reset_metrics()
            metrics_after = auth_service.get_metrics()
            assert metrics_after["total_requests"] == 0

    def test_metrics_key_masking(self):
        """Test que las métricas enmascaran las claves por seguridad."""
        with patch.dict(os.environ, {"AUTH_KEY": "sk-1234567890abcdefghijklmnopqrstuvwxyz"}, clear=True):
            auth_service = AuthService()
            
            auth_service.record_request("sk-1234567890abcdefghijklmnopqrstuvwxyz", success=True)
            metrics = auth_service.get_metrics()
            
            # La clave debe estar enmascarada en las métricas
            masked_keys = list(metrics["keys_metrics"].keys())
            assert len(masked_keys) == 1
            assert "sk-1" in masked_keys[0]
            assert "wxyz" in masked_keys[0]
            assert "..." in masked_keys[0]
