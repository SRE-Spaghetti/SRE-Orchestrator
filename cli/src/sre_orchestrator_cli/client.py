"""Orchestrator API client for making HTTP requests."""

import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime


class OrchestratorClientError(Exception):
    """Base exception for orchestrator client errors."""
    pass


class ConnectionError(OrchestratorClientError):
    """Raised when connection to orchestrator fails."""
    pass


class AuthenticationError(OrchestratorClientError):
    """Raised when authentication fails."""
    pass


class NotFoundError(OrchestratorClientError):
    """Raised when a resource is not found."""
    pass


class OrchestratorClient:
    """Client for interacting with the SRE Orchestrator API."""

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: float = 60.0):
        """
        Initialize the orchestrator client.

        Args:
            base_url: Base URL of the orchestrator service
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    def _get_client(self) -> httpx.AsyncClient:
        """Get the HTTP client, creating it if necessary."""
        if self._client is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout
            )
        return self._client

    async def create_incident(self, description: str) -> str:
        """
        Create a new incident and start investigation.

        Args:
            description: Natural language description of the incident

        Returns:
            Incident ID

        Raises:
            ConnectionError: If connection to orchestrator fails
            AuthenticationError: If authentication fails
            OrchestratorClientError: For other API errors
        """
        client = self._get_client()

        try:
            response = await client.post(
                "/api/v1/incidents",
                json={"description": description}
            )

            if response.status_code == 401:
                raise AuthenticationError("Authentication failed. Check your API key.")
            elif response.status_code == 403:
                raise AuthenticationError("Access forbidden. Check your permissions.")
            elif response.status_code >= 400:
                error_detail = response.json().get("detail", "Unknown error")
                raise OrchestratorClientError(f"API error: {error_detail}")

            response.raise_for_status()
            data = response.json()
            return data["id"]

        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to orchestrator at {self.base_url}: {e}")
        except httpx.TimeoutException:
            raise ConnectionError(f"Request timed out after {self.timeout} seconds")
        except httpx.HTTPError as e:
            raise OrchestratorClientError(f"HTTP error: {e}")

    async def get_incident(self, incident_id: str) -> Dict[str, Any]:
        """
        Get incident details by ID.

        Args:
            incident_id: Incident ID

        Returns:
            Incident data dictionary

        Raises:
            NotFoundError: If incident not found
            ConnectionError: If connection to orchestrator fails
            OrchestratorClientError: For other API errors
        """
        client = self._get_client()

        try:
            response = await client.get(f"/api/v1/incidents/{incident_id}")

            if response.status_code == 404:
                raise NotFoundError(f"Incident {incident_id} not found")
            elif response.status_code == 401:
                raise AuthenticationError("Authentication failed. Check your API key.")
            elif response.status_code >= 400:
                error_detail = response.json().get("detail", "Unknown error")
                raise OrchestratorClientError(f"API error: {error_detail}")

            response.raise_for_status()
            return response.json()

        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to orchestrator at {self.base_url}: {e}")
        except httpx.TimeoutException:
            raise ConnectionError(f"Request timed out after {self.timeout} seconds")
        except httpx.HTTPError as e:
            raise OrchestratorClientError(f"HTTP error: {e}")

    async def list_incidents(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent incidents.

        Args:
            limit: Maximum number of incidents to return

        Returns:
            List of incident data dictionaries

        Raises:
            ConnectionError: If connection to orchestrator fails
            OrchestratorClientError: For other API errors
        """
        client = self._get_client()

        try:
            response = await client.get(
                "/api/v1/incidents",
                params={"limit": limit}
            )

            if response.status_code == 401:
                raise AuthenticationError("Authentication failed. Check your API key.")
            elif response.status_code >= 400:
                error_detail = response.json().get("detail", "Unknown error")
                raise OrchestratorClientError(f"API error: {error_detail}")

            response.raise_for_status()
            return response.json()

        except httpx.ConnectError as e:
            raise ConnectionError(f"Failed to connect to orchestrator at {self.base_url}: {e}")
        except httpx.TimeoutException:
            raise ConnectionError(f"Request timed out after {self.timeout} seconds")
        except httpx.HTTPError as e:
            raise OrchestratorClientError(f"HTTP error: {e}")

    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
