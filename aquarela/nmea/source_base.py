"""Abstract base class for NMEA 2000 data sources."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Tuple


class NmeaSource(ABC):
    """Abstract base for PGN data sources.

    Implementations:
    - SimulatorSource: generates synthetic PGN frames for development/testing
    - CanSource: reads real PGN frames from Waveshare CAN HAT via SocketCAN
    """

    @abstractmethod
    async def start(self) -> None:
        """Initialize the data source."""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Shut down the data source."""
        ...

    @property
    def pgns_per_step(self) -> int:
        """Number of PGN frames yielded per time step.

        The pipeline uses this to detect step boundaries and trigger
        the full processing chain (calibration, true wind, targets, …).
        """
        return 7

    @abstractmethod
    async def stream(self) -> AsyncIterator[Tuple[int, bytes]]:
        """Yield (pgn_number, data_bytes) tuples as they arrive.

        Each tuple represents a single decoded NMEA 2000 message.
        The consumer should call decode_pgn() on each tuple.
        """
        ...
