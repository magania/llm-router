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
Authentication service for OpenAI API compatible authentication.
"""
import os
import time
from typing import Dict, List, Optional, Set
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling API key authentication and metrics."""
    
    def __init__(self):
        self.valid_keys: Set[str] = set()
        self.request_metrics: Dict[str, Dict[str, any]] = defaultdict(lambda: {
            'requests_count': 0,
            'first_request': None,
            'last_request': None,
            'total_errors': 0,
            'total_success': 0
        })
        self._load_auth_keys()
    
    def _load_auth_keys(self) -> None:
        """Load authentication keys from environment variables."""
        self.valid_keys.clear()
        
        # Check for single AUTH_KEY first
        auth_key = os.getenv('AUTH_KEY')
        if auth_key:
            self.valid_keys.add(auth_key.strip())
            logger.info("Loaded single AUTH_KEY")
            return
        
        # If AUTH_KEY not present, look for AUTH_KEY_01, AUTH_KEY_02, etc.
        key_index = 1
        while True:
            key_name = f'AUTH_KEY_{key_index:02d}'  # 01, 02, 03, etc.
            key_value = os.getenv(key_name)
            
            if key_value is None:
                # Stop at first missing key (no gaps allowed)
                break
            
            self.valid_keys.add(key_value.strip())
            key_index += 1
        
        if self.valid_keys:
            logger.info(f"Loaded {len(self.valid_keys)} authentication keys from AUTH_KEY_01 through AUTH_KEY_{key_index-1:02d}")
        else:
            logger.warning("No authentication keys found in environment variables")
    
    def reload_keys(self) -> None:
        """Reload authentication keys from environment variables."""
        self._load_auth_keys()
    
    def is_valid_key(self, api_key: str) -> bool:
        """Check if the provided API key is valid."""
        if not api_key:
            return False
        
        # Remove 'Bearer ' prefix if present
        if api_key.startswith('Bearer '):
            api_key = api_key[7:]
        
        return api_key.strip() in self.valid_keys
    
    def get_valid_keys_count(self) -> int:
        """Get the number of valid keys loaded."""
        return len(self.valid_keys)
    
    def record_request(self, api_key: str, success: bool = True) -> None:
        """Record a request for metrics tracking."""
        if not api_key:
            return
        
        # Remove 'Bearer ' prefix if present
        if api_key.startswith('Bearer '):
            api_key = api_key[7:]
        
        api_key = api_key.strip()
        current_time = time.time()
        
        metrics = self.request_metrics[api_key]
        metrics['requests_count'] += 1
        metrics['last_request'] = current_time
        
        if metrics['first_request'] is None:
            metrics['first_request'] = current_time
        
        if success:
            metrics['total_success'] += 1
        else:
            metrics['total_errors'] += 1
    
    def get_metrics(self) -> Dict[str, any]:
        """Get authentication and usage metrics."""
        total_requests = sum(metrics['requests_count'] for metrics in self.request_metrics.values())
        total_success = sum(metrics['total_success'] for metrics in self.request_metrics.values())
        total_errors = sum(metrics['total_errors'] for metrics in self.request_metrics.values())
        
        # Create summary by masking keys for security
        key_metrics = {}
        for api_key, metrics in self.request_metrics.items():
            # Mask the key for security (show first 4 and last 4 chars)
            masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else f"{api_key[:2]}...{api_key[-2:]}"
            
            key_metrics[masked_key] = {
                'requests_count': metrics['requests_count'],
                'success_count': metrics['total_success'],
                'error_count': metrics['total_errors'],
                'first_request': metrics['first_request'],
                'last_request': metrics['last_request'],
                'success_rate': metrics['total_success'] / max(metrics['requests_count'], 1) * 100
            }
        
        return {
            'valid_keys_count': len(self.valid_keys),
            'total_requests': total_requests,
            'total_success': total_success,
            'total_errors': total_errors,
            'success_rate': total_success / max(total_requests, 1) * 100,
            'keys_metrics': key_metrics,
            'active_keys': len([k for k in self.request_metrics.keys() if self.request_metrics[k]['requests_count'] > 0])
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics."""
        self.request_metrics.clear()
        logger.info("Authentication metrics reset")
    
    def get_key_metrics(self, api_key: str) -> Optional[Dict[str, any]]:
        """Get metrics for a specific API key."""
        if not api_key:
            return None
            
        # Remove 'Bearer ' prefix if present
        if api_key.startswith('Bearer '):
            api_key = api_key[7:]
        
        api_key = api_key.strip()
        
        if api_key in self.request_metrics:
            metrics = self.request_metrics[api_key]
            return {
                'requests_count': metrics['requests_count'],
                'success_count': metrics['total_success'],
                'error_count': metrics['total_errors'],
                'first_request': metrics['first_request'],
                'last_request': metrics['last_request'],
                'success_rate': metrics['total_success'] / max(metrics['requests_count'], 1) * 100
            }
        
        return None
