"""
This file is part of Hydraulic Engine
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
import os
import sys
import platform
from pathlib import Path
from typing import Optional


def get_datadir() -> str:
    """
    Returns a parent directory path where persistent application data can be stored.

    - Linux: ~/.local/share
    - macOS: ~/Library/Application Support
    - Windows: C:/Users/<USER>/AppData/Roaming

    :return: Path to data directory
    """
    home = Path.home()
    system = platform.system()

    if system == "Windows":
        return str(home / "AppData" / "Roaming")
    elif system == "Linux":
        return str(home / ".local" / "share")
    elif system == "Darwin":  # macOS
        return str(home / "Library" / "Application Support")
    else:
        return str(home)


def get_config_dir() -> str:
    """
    Returns a parent directory path where configuration files can be stored.

    - Linux: ~/.config
    - macOS: ~/Library/Preferences
    - Windows: C:/Users/<USER>/AppData/Local

    :return: Path to config directory
    """
    home = Path.home()
    system = platform.system()

    if system == "Windows":
        return str(home / "AppData" / "Local")
    elif system == "Linux":
        return str(home / ".config")
    elif system == "Darwin":  # macOS
        return str(home / "Library" / "Preferences")
    else:
        return str(home)


def get_temp_dir() -> str:
    """
    Returns the system temporary directory.

    :return: Path to temporary directory
    """
    import tempfile
    return tempfile.gettempdir()


def ensure_dir(path: str) -> bool:
    """
    Ensure that a directory exists, creating it if necessary.

    :param path: Path to the directory
    :return: True if directory exists or was created, False on error
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except OSError:
        return False


def file_exists(path: str) -> bool:
    """
    Check if a file exists.

    :param path: Path to the file
    :return: True if file exists
    """
    return os.path.isfile(path)


def dir_exists(path: str) -> bool:
    """
    Check if a directory exists.

    :param path: Path to the directory
    :return: True if directory exists
    """
    return os.path.isdir(path)


def get_file_extension(path: str) -> str:
    """
    Get the file extension from a path.

    :param path: Path to the file
    :return: File extension (with dot, e.g., '.inp')
    """
    return os.path.splitext(path)[1]


def get_filename(path: str, with_extension: bool = True) -> str:
    """
    Get the filename from a path.

    :param path: Path to the file
    :param with_extension: Include extension in result
    :return: Filename
    """
    if with_extension:
        return os.path.basename(path)
    return os.path.splitext(os.path.basename(path))[0]


def join_path(*args: str) -> str:
    """
    Join path components.

    :param args: Path components
    :return: Joined path
    """
    return os.path.join(*args)


def get_python_version() -> str:
    """
    Get the current Python version.

    :return: Python version string
    """
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_platform_info() -> dict:
    """
    Get platform information.

    :return: Dictionary with platform info
    """
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python_version": get_python_version(),
    }
