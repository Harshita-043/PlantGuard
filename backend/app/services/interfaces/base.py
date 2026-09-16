"""
Base service interface for all ML services
"""
from abc import ABC, abstractmethod
from typing import Any


class BaseService(ABC):
    """
    Base interface for all ML services in PlantGuard AI.
    All services should inherit from this base class.
    """

    @abstractmethod
    def initialize(self) -> None:
        """
        Initialize the service. Called once during application startup.
        """
        pass

    @abstractmethod
    def is_ready(self) -> bool:
        """
        Check if the service is ready to process requests.

        Returns:
            bool: True if service is ready, False otherwise
        """
        pass

    @abstractmethod
    def get_service_name(self) -> str:
        """
        Get the name of the service.

        Returns:
            str: Service name
        """
        pass