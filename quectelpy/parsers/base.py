"""
Base parser classes and utilities.

Provides reusable parsing functionality for AT command responses.
"""

import logging
from abc import ABC, abstractmethod
from typing import TypeVar, Generic

from ..exceptions import ATParseError

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ResponseParser(ABC, Generic[T]):
    """
    Abstract base class for response parsers.

    Parsers convert raw AT command responses into typed data structures.
    """

    @abstractmethod
    def parse(self, response: list[str]) -> T:
        """
        Parse AT command response.

        Args:
            response: List of response lines from modem

        Returns:
            Parsed data structure

        Raises:
            ATParseError: If response cannot be parsed
        """
        pass


class SimpleValueParser(ResponseParser[str]):
    """Parser for simple single-value responses."""

    def __init__(self, expected_lines: int = 1):
        """
        Initialize parser.

        Args:
            expected_lines: Number of response lines expected
        """
        self.expected_lines = expected_lines

    def parse(self, response: list[str]) -> str:
        """Parse simple value response."""
        if len(response) != self.expected_lines:
            raise ATParseError(
                f"Expected {self.expected_lines} lines, got {len(response)}",
                response=response
            )
        return response[0]


class IntValueParser(ResponseParser[int]):
    """Parser for integer value responses."""

    def parse(self, response: list[str]) -> int:
        """Parse integer value."""
        if not response:
            raise ATParseError("Empty response", response=response)

        try:
            return int(response[0])
        except ValueError as e:
            raise ATParseError(
                f"Failed to parse integer: {response[0]}",
                response=response
            ) from e


class CommaSeparatedParser(ResponseParser[list[str]]):
    """Parser for comma-separated values."""

    def __init__(self, expected_parts: int | None = None):
        """
        Initialize parser.

        Args:
            expected_parts: Expected number of parts (None = any)
        """
        self.expected_parts = expected_parts

    def parse(self, response: list[str]) -> list[str]:
        """Parse comma-separated values."""
        if not response:
            raise ATParseError("Empty response", response=response)

        parts = [p.strip().strip('"') for p in response[0].split(",")]

        if self.expected_parts is not None and len(parts) != self.expected_parts:
            raise ATParseError(
                f"Expected {self.expected_parts} parts, got {len(parts)}",
                response=response
            )

        return parts
