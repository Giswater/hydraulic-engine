"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

EPANET module tests.
"""
# -*- coding: utf-8 -*-
import pytest


class TestEpanetImports:
    """Test EPANET module imports."""

    def test_import_from_package(self):
        """Test importing EPANET classes from main package."""
        from hydraulic_engine import EpanetRunner, EpanetInpHandler, EpanetRptHandler
        assert EpanetRunner is not None
        assert EpanetInpHandler is not None
        assert EpanetRptHandler is not None

    def test_import_from_core(self):
        """Test importing from core.epanet."""
        from hydraulic_engine.core.epanet import EpanetRunner, EpanetInpHandler, EpanetRptHandler
        assert EpanetRunner is not None
        assert EpanetInpHandler is not None
        assert EpanetRptHandler is not None

    def test_import_result_classes(self):
        """Test importing result dataclasses."""
        from hydraulic_engine.core.epanet.runner import EpanetRunResult, EpanetRunStatus
        assert EpanetRunResult is not None
        assert EpanetRunStatus is not None


class TestEpanetRunner:
    """Test EpanetRunner class."""

    def test_runner_initialization(self):
        """Test EpanetRunner can be initialized."""
        from hydraulic_engine import EpanetRunner
        runner = EpanetRunner()
        assert runner is not None

    def test_run_missing_file(self):
        """Test running with missing INP file."""
        from hydraulic_engine import EpanetRunner
        from hydraulic_engine.core.epanet.runner import EpanetRunStatus
        
        runner = EpanetRunner()
        result = runner.run("nonexistent.inp")
        
        assert result.status == EpanetRunStatus.ERROR
        assert len(result.errors) > 0

    def test_validate_missing_file(self):
        """Test validating missing INP file."""
        from hydraulic_engine import EpanetRunner
        
        runner = EpanetRunner()
        validation = runner.validate_inp("nonexistent.inp")
        
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0


class TestEpanetInpHandler:
    """Test EpanetInpHandler class."""

    def test_handler_initialization(self):
        """Test EpanetInpHandler can be initialized."""
        from hydraulic_engine import EpanetInpHandler
        handler = EpanetInpHandler()
        assert handler is not None
        assert handler.inp_path is None
        assert handler.wn is None

    def test_is_loaded_false(self):
        """Test is_loaded returns False when no file loaded."""
        from hydraulic_engine import EpanetInpHandler
        handler = EpanetInpHandler()
        assert handler.is_loaded() is False

    def test_read_missing_file(self):
        """Test reading missing file."""
        from hydraulic_engine import EpanetInpHandler
        handler = EpanetInpHandler()
        result = handler.read("nonexistent.inp")
        assert result is False
        assert handler.error_msg is not None

    def test_get_summary_not_loaded(self):
        """Test get_summary when no file loaded."""
        from hydraulic_engine import EpanetInpHandler
        handler = EpanetInpHandler()
        summary = handler.get_summary()
        assert summary["loaded"] is False


class TestEpanetRptHandler:
    """Test EpanetRptHandler class."""

    def test_handler_initialization(self):
        """Test EpanetRptHandler can be initialized."""
        from hydraulic_engine import EpanetRptHandler
        handler = EpanetRptHandler()
        assert handler is not None
        assert handler.rpt_path is None

    def test_is_loaded_false(self):
        """Test is_loaded returns False when no file loaded."""
        from hydraulic_engine import EpanetRptHandler
        handler = EpanetRptHandler()
        assert handler.is_loaded() is False

    def test_read_missing_file(self):
        """Test reading missing file."""
        from hydraulic_engine import EpanetRptHandler
        handler = EpanetRptHandler()
        result = handler.read("nonexistent.rpt")
        assert result is False
        assert handler.error_msg is not None

    def test_get_summary_not_loaded(self):
        """Test get_summary when no file loaded."""
        from hydraulic_engine import EpanetRptHandler
        handler = EpanetRptHandler()
        summary = handler.get_summary()
        assert summary["loaded"] is False
