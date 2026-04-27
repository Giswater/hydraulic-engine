"""
Custom exceptions for hydraulic_engine.
"""
# -*- coding: utf-8 -*-


class HydraulicEngineError(Exception):
    """Base exception for all hydraulic_engine errors."""


class FileLoadError(HydraulicEngineError):
    """Raised when a file cannot be loaded."""


class FileWriteError(HydraulicEngineError):
    """Raised when a file cannot be written."""


class UnsupportedFileTypeError(HydraulicEngineError):
    """Raised when an unsupported file type is provided."""
