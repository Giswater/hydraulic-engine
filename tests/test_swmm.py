"""
This file is part of Hydraulic Engine
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

SWMM module tests.
"""
# -*- coding: utf-8 -*-
import os
import pytest


class TestSwmmImports:
    """Test SWMM module imports."""

    def test_import_from_package(self):
        """Test importing SWMM classes from main package."""
        from hydraulic_engine import SwmmRunner, SwmmInpHandler, SwmmRptHandler
        assert SwmmRunner is not None
        assert SwmmInpHandler is not None
        assert SwmmRptHandler is not None

    def test_import_from_core(self):
        """Test importing from core.swmm."""
        from hydraulic_engine.core.swmm import SwmmRunner, SwmmInpHandler, SwmmRptHandler
        assert SwmmRunner is not None
        assert SwmmInpHandler is not None
        assert SwmmRptHandler is not None

    def test_import_result_classes(self):
        """Test importing result dataclasses."""
        from hydraulic_engine.core.swmm.runner import SwmmRunResult, SwmmRunStatus
        assert SwmmRunResult is not None
        assert SwmmRunStatus is not None


class TestSwmmRunner:
    """Test SwmmRunner class."""

    def test_runner_initialization(self):
        """Test SwmmRunner can be initialized."""
        from hydraulic_engine import SwmmRunner
        runner = SwmmRunner()
        assert runner is not None

    def test_run_missing_file(self):
        """Test running with missing INP file."""
        from hydraulic_engine import SwmmRunner
        from hydraulic_engine.core.swmm.runner import SwmmRunStatus
        
        runner = SwmmRunner()
        result = runner.run("nonexistent.inp")
        
        assert result.status == SwmmRunStatus.ERROR
        assert len(result.errors) > 0
        assert "not found" in result.errors[0].lower()

    def test_validate_missing_file(self):
        """Test validating missing INP file."""
        from hydraulic_engine import SwmmRunner
        
        runner = SwmmRunner()
        validation = runner.validate_inp("nonexistent.inp")
        
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0

    def test_progress_callback(self):
        """Test progress callback functionality."""
        from hydraulic_engine import SwmmRunner
        
        progress_calls = []
        
        def callback(progress, message):
            progress_calls.append((progress, message))
        
        runner = SwmmRunner()
        runner.set_progress_callback(callback)
        runner._report_progress(50, "Test message")
        
        assert len(progress_calls) == 1
        assert progress_calls[0] == (50, "Test message")


class TestSwmmInpHandler:
    """Test SwmmInpHandler class."""

    def test_handler_initialization(self):
        """Test SwmmInpHandler can be initialized."""
        from hydraulic_engine import SwmmInpHandler
        handler = SwmmInpHandler()
        assert handler is not None
        assert handler.inp_path is None
        assert handler.inp is None

    def test_is_loaded_false(self):
        """Test is_loaded returns False when no file loaded."""
        from hydraulic_engine import SwmmInpHandler
        handler = SwmmInpHandler()
        assert handler.is_loaded() is False

    def test_read_missing_file(self):
        """Test reading missing file."""
        from hydraulic_engine import SwmmInpHandler
        handler = SwmmInpHandler()
        result = handler.read("nonexistent.inp")
        assert result is False
        assert handler.error_msg is not None

    def test_get_summary_not_loaded(self):
        """Test get_summary when no file loaded."""
        from hydraulic_engine import SwmmInpHandler
        handler = SwmmInpHandler()
        summary = handler.get_summary()
        assert summary["loaded"] is False


class TestSwmmRptHandler:
    """Test SwmmRptHandler class."""

    def test_handler_initialization(self):
        """Test SwmmRptHandler can be initialized."""
        from hydraulic_engine import SwmmRptHandler
        handler = SwmmRptHandler()
        assert handler is not None
        assert handler.rpt_path is None

    def test_is_loaded_false(self):
        """Test is_loaded returns False when no file loaded."""
        from hydraulic_engine import SwmmRptHandler
        handler = SwmmRptHandler()
        assert handler.is_loaded() is False

    def test_read_missing_file(self):
        """Test reading missing file."""
        from hydraulic_engine import SwmmRptHandler
        handler = SwmmRptHandler()
        result = handler.read("nonexistent.rpt")
        assert result is False
        assert handler.error_msg is not None

    def test_get_summary_not_loaded(self):
        """Test get_summary when no file loaded."""
        from hydraulic_engine import SwmmRptHandler
        handler = SwmmRptHandler()
        summary = handler.get_summary()
        assert summary["loaded"] is False


class TestSwmmIntegration:
    """Integration tests for SWMM module (require swmm-api)."""

    @pytest.mark.skip(reason="Requires actual INP file")
    def test_full_workflow(self, tmp_path):
        """Test complete SWMM workflow."""
        from hydraulic_engine import SwmmRunner, SwmmInpHandler, SwmmRptHandler
        
        # Read INP
        inp_handler = SwmmInpHandler()
        inp_handler.read("sample.inp")
        
        # Run simulation
        runner = SwmmRunner()
        result = runner.run("sample.inp", rpt_path=str(tmp_path / "result.rpt"))
        
        # Read results
        rpt_handler = SwmmRptHandler()
        rpt_handler.read(result.rpt_path)
        
        assert result.status.value in ("success", "warning")
