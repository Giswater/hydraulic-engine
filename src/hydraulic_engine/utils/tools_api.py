"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time
import requests

from . import tools_log


class ApiType(Enum):
    """API type enumeration"""
    FROST = "frost"  # SensorThings API (FROST-Server)
    # Future: Add other APIs as needed


@dataclass
class KeycloakAuth:
    """Keycloak authentication configuration."""
    url: str
    realm: str
    client_id: str
    client_secret: str
    _token: Optional[str] = None
    _token_expiry: float = 0

    def get_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        current_time = time.time()

        # Check if token is still valid (with 30s buffer)
        if self._token and current_time < self._token_expiry - 30:
            return self._token

        # Request new token
        token_url = f"{self.url}/realms/{self.realm}/protocol/openid-connect/token"

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        response = requests.post(token_url, data=data)
        response.raise_for_status()

        token_data = response.json()
        self._token = token_data["access_token"]
        # Set expiry based on expires_in, default to 300s if not provided
        expires_in = token_data.get("expires_in", 300)
        self._token_expiry = current_time + expires_in

        tools_log.log_info("Keycloak token obtained/refreshed")
        return self._token

    def get_auth_header(self) -> Dict[str, str]:
        """Get the Authorization header with Bearer token."""
        return {"Authorization": f"Bearer {self.get_token()}"}


class HeApiClient(ABC):
    """
    Abstract base class for API clients.
    Provides interface for REST API operations.
    """

    def __init__(self):
        self.base_url: Optional[str] = None
        self.last_error: Optional[str] = None
        self.api_type: Optional[ApiType] = None
        self.session: Optional[requests.Session] = None

    @abstractmethod
    def connect(self, **kwargs) -> bool:
        """Connect/configure the API client."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the API client connection."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if API client is configured."""
        pass


class HeFrostClient(HeApiClient):
    """
    FROST-Server (SensorThings API) client.
    Handles connections and operations for SensorThings API.
    Supports optional Keycloak authentication.
    """

    def __init__(self):
        super().__init__()
        self.api_type = ApiType.FROST
        self.auth: Optional[KeycloakAuth] = None

    def connect(
        self,
        base_url: str,
        keycloak_url: Optional[str] = None,
        keycloak_realm: Optional[str] = None,
        keycloak_client_id: Optional[str] = None,
        keycloak_client_secret: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        Configure FROST-Server connection with optional Keycloak authentication.

        :param base_url: Base URL of FROST-Server (e.g., "http://localhost:8080/FROST-Server/v1.1/")
        :param keycloak_url: Keycloak server URL (optional)
        :param keycloak_realm: Keycloak realm (optional)
        :param keycloak_client_id: Keycloak client ID (optional)
        :param keycloak_client_secret: Keycloak client secret (optional)
        :return: True if configuration successful
        """
        try:
            self.base_url = base_url.rstrip('/') + '/'
            self.session = requests.Session()

            # Configure Keycloak authentication if all parameters provided
            if all([keycloak_url, keycloak_realm, keycloak_client_id, keycloak_client_secret]):
                self.auth = KeycloakAuth(
                    url=keycloak_url,
                    realm=keycloak_realm,
                    client_id=keycloak_client_id,
                    client_secret=keycloak_client_secret
                )
                tools_log.log_info("Keycloak authentication enabled")

            # Test connection
            headers = self._get_headers()
            response = self.session.get(self.base_url, headers=headers)
            response.raise_for_status()

            tools_log.log_info(f"Connected to FROST-Server: {self.base_url}")
            return True

        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"FROST-Server connection error: {e}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers, including auth if configured."""
        headers = {"Content-Type": "application/json"}
        if self.auth:
            headers.update(self.auth.get_auth_header())
        return headers

    def close(self) -> None:
        """Close the session."""
        if self.session:
            self.session.close()
            self.session = None
        self.auth = None
        tools_log.log_info("FROST-Server connection closed")

    def is_connected(self) -> bool:
        """Check if client is configured."""
        return self.base_url is not None and self.session is not None

    # HTTP Methods
    def get(self, endpoint: str) -> requests.Response:
        """Send GET request to endpoint."""
        url = f'{self.base_url}{endpoint}' if not endpoint.startswith('http') else endpoint
        response = self.session.get(url, headers=self._get_headers())
        response.raise_for_status()
        return response

    def post(self, endpoint: str, data: Dict) -> requests.Response:
        """Send POST request to endpoint."""
        url = f'{self.base_url}{endpoint}'
        response = self.session.post(url, json=data, headers=self._get_headers())
        response.raise_for_status()
        return response

    def patch(self, endpoint: str, data: Dict) -> requests.Response:
        """Send PATCH request to endpoint."""
        url = f'{self.base_url}{endpoint}'
        response = self.session.patch(url, json=data, headers=self._get_headers())
        response.raise_for_status()
        return response

    def delete(self, endpoint: str) -> requests.Response:
        """Send DELETE request to endpoint."""
        url = f'{self.base_url}{endpoint}'
        response = self.session.delete(url, headers=self._get_headers())
        response.raise_for_status()
        return response

    # Core CRUD operations
    def create_entity(self, entity_type: str, data: Dict) -> Optional[str]:
        """Create an entity and return its URL."""
        try:
            response = self.post(entity_type, data)
            return response.headers.get('Location')
        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Error creating {entity_type}: {e}")
            return None

    def update_entity(self, entity_type: str, entity_id: str, data: Dict) -> bool:
        """Update an entity using PATCH."""
        try:
            self.patch(f'{entity_type}({entity_id})', data)
            return True
        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Error updating {entity_type}({entity_id}): {e}")
            return False

    def delete_entity(self, entity_type: str, entity_id: str) -> bool:
        """Delete an entity."""
        try:
            self.delete(f'{entity_type}({entity_id})')
            return True
        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Error deleting {entity_type}({entity_id}): {e}")
            return False

    def get_entities(self, entity_type: str, expand: Optional[str] = None,
                     top: int = 1000) -> Optional[List[Dict]]:
        """Get all entities with pagination support."""
        try:
            entities = []
            endpoint = f'{entity_type}?$top={top}'
            if expand:
                endpoint += f'&$expand={expand}'

            while endpoint:
                response = self.get(endpoint)
                data = response.json()

                if 'value' in data:
                    entities.extend(data['value'])

                # Handle pagination
                next_link = data.get('@iot.nextLink')
                if next_link:
                    # Extract relative path from full URL
                    endpoint = next_link.replace(self.base_url, '')
                else:
                    endpoint = None

            return entities

        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Error getting {entity_type}: {e}")
            return None

    def _send_single_batch(self, batch: List[Dict], batch_num: int) -> Tuple[int, List[Dict], float]:
        """
        Send a single batch request. Used by ThreadPoolExecutor.

        Returns:
            Tuple of (batch_num, responses, elapsed_time)
        """
        batch_start = time.time()
        response = self.post('$batch', {"requests": batch})
        responses = response.json().get('responses', [])
        elapsed = time.time() - batch_start
        return batch_num, responses, elapsed

    def batch_request(self, batch_requests: List[Dict],
                      batch_size: int = 50, max_workers: int = 4) -> Optional[List[Dict]]:
        """
        Send multiple operations in a single HTTP request using FROST-Server's JSON Batch Request.
        Splits into multiple batches and sends them concurrently for better performance.

        :param batch_requests: List of request dicts with 'id', 'method', 'url', and optionally 'body'
        :param batch_size: Maximum number of operations per batch request
        :param max_workers: Number of concurrent batch requests (default: 4)
        :return: List of response dicts from all batches
        """
        try:
            total_requests = len(batch_requests)
            num_batches = (total_requests + batch_size - 1) // batch_size

            # Split into batches
            batches = []
            for i in range(0, total_requests, batch_size):
                batches.append(batch_requests[i:i + batch_size])

            # Track results by batch number to maintain order
            results_by_batch = {}
            total_success = 0
            total_failed = 0
            completed = 0

            # Thread-safe counter for progress
            lock = threading.Lock()

            total_start = time.time()

            tools_log.log_info(f"  Sending {num_batches} batches with {max_workers} concurrent workers...")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all batches
                futures = {
                    executor.submit(self._send_single_batch, batch, batch_num): batch_num
                    for batch_num, batch in enumerate(batches, 1)
                }

                # Process results as they complete
                for future in as_completed(futures):
                    batch_num, responses, batch_time = future.result()
                    results_by_batch[batch_num] = responses

                    # Count successes/failures
                    success = sum(1 for r in responses if 200 <= r.get('status', 0) < 300)
                    failed = len(responses) - success

                    with lock:
                        completed += 1
                        total_success += success
                        total_failed += failed
                        elapsed = time.time() - total_start
                        ops_done = sum(len(r) for r in results_by_batch.values())

                        tools_log.log_info(
                            f"  Batch {batch_num}/{num_batches}: {len(responses)} ops in {batch_time:.2f}s "
                            f"({success} ok, {failed} err) - Progress: {completed}/{num_batches} batches, "
                            f"{ops_done}/{total_requests} ops ({elapsed:.1f}s)"
                        )

            # Reassemble responses in original order
            all_responses = []
            for batch_num in range(1, num_batches + 1):
                all_responses.extend(results_by_batch[batch_num])

            total_time = time.time() - total_start
            ops_per_sec = total_requests / total_time if total_time > 0 else 0
            tools_log.log_info(
                f"  All batches complete: {total_success} ok, {total_failed} err in "
                f"{total_time:.2f}s ({ops_per_sec:.1f} ops/sec)"
            )

            return all_responses

        except Exception as e:
            self.last_error = str(e)
            tools_log.log_error(f"Batch request error: {e}")
            return None


# Global API client management
def create_frost_connection(
    base_url: str,
    keycloak_url: Optional[str] = None,
    keycloak_realm: Optional[str] = None,
    keycloak_client_id: Optional[str] = None,
    keycloak_client_secret: Optional[str] = None,
    set_as_default: bool = True,
    **kwargs
) -> Optional[HeFrostClient]:
    """
    Create a FROST-Server connection with optional Keycloak authentication.

    :param base_url: Base URL of FROST-Server
    :param keycloak_url: Keycloak server URL (optional)
    :param keycloak_realm: Keycloak realm (optional)
    :param keycloak_client_id: Keycloak client ID (optional)
    :param keycloak_client_secret: Keycloak client secret (optional)
    :param set_as_default: Set this as the default global API client
    :return: HeFrostClient instance or None
    """
    from ..config import config

    client = HeFrostClient()
    if client.connect(
        base_url,
        keycloak_url=keycloak_url,
        keycloak_realm=keycloak_realm,
        keycloak_client_id=keycloak_client_id,
        keycloak_client_secret=keycloak_client_secret,
        **kwargs
    ):
        if set_as_default:
            config.session_vars['api_client'] = client
        return client
    return None


def get_api_client() -> Optional[HeApiClient]:
    """Get the current default API client."""
    from ..config import config
    return config.session_vars.get('api_client')


def close_api_client() -> None:
    """Close the current default API client."""
    from ..config import config
    client = config.session_vars.get('api_client')
    if client:
        client.close()
        config.session_vars['api_client'] = None
