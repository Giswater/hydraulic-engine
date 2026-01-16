"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

Basic package tests.
"""
# -*- coding: utf-8 -*-
import pytest


class TestPackageImport:
    """Test package import functionality."""

    def test_import_package(self):
        """Test that package can be imported."""
        import hydraulic_engine
        assert hydraulic_engine is not None

    def test_package_version(self):
        """Test that package version is defined."""
        from hydraulic_engine import __version__
        assert __version__ is not None
        assert isinstance(__version__, str)

    def test_import_config(self):
        """Test that config module can be imported."""
        from hydraulic_engine import config
        assert config is not None

    def test_import_utils(self):
        """Test that utils module can be imported."""
        from hydraulic_engine.utils import tools_log
        assert tools_log is not None


class TestConfig:
    """Test config module."""

    def test_project_types(self):
        """Test HeProjectType enum."""
        from hydraulic_engine.config import HeProjectType
        assert HeProjectType.WS.value == "ws"
        assert HeProjectType.UD.value == "ud"

    def test_simulators(self):
        """Test HeSimulator enum."""
        from hydraulic_engine.config import HeSimulator
        assert HeSimulator.EPANET.value == "epanet"
        assert HeSimulator.SWMM.value == "swmm"

    def test_init_global(self):
        """Test init_global function."""
        from hydraulic_engine import config
        config.init_config("/test/path", "test_package", "/test/user")
        assert config.package_dir == "/test/path"
        assert config.package_name == "test_package"
        assert config.user_folder_dir == "/test/user"
