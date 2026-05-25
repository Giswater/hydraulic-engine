"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

SWMM module tests.
"""
# -*- coding: utf-8 -*-
import pytest

from hydraulic_engine import FileLoadError, ModelNotLoadedError
from hydraulic_engine.swmm import SwmmRunner, SwmmInpHandler, SwmmRptHandler, SwmmOutHandler
from hydraulic_engine.utils.enums import RunStatus


class TestSwmmImports:
    """Test SWMM module imports."""

    def test_import_from_package(self):
        from hydraulic_engine import swmm
        assert SwmmRunner is not None
        assert swmm.SwmmInpHandler is not None
        assert swmm.SwmmRptHandler is not None

    def test_import_result_classes(self):
        from hydraulic_engine.swmm.runner import SwmmRunResult
        assert SwmmRunResult is not None


class TestSwmmRunner:
    """Test SwmmRunner class."""

    def test_runner_initialization(self):
        runner = SwmmRunner(inp_path="model.inp")
        assert runner is not None

    def test_run_missing_file_raises(self):
        runner = SwmmRunner(inp_path="nonexistent.inp")
        with pytest.raises(FileLoadError):
            runner.run()

    def test_progress_callback(self):
        progress_calls = []

        def callback(progress, message):
            progress_calls.append((progress, message))

        runner = SwmmRunner(progress_callback=callback)
        runner._report_progress(50, "Test message")

        assert len(progress_calls) == 1
        assert progress_calls[0] == (50, "Test message")


class TestSwmmInpHandler:
    """Test SwmmInpHandler class."""

    def test_handler_initialization(self):
        handler = SwmmInpHandler()
        assert handler is not None
        assert handler.file_path is None

    def test_is_loaded_false(self):
        handler = SwmmInpHandler()
        assert handler.is_loaded() is False

    def test_load_missing_file_raises(self):
        handler = SwmmInpHandler()
        with pytest.raises(FileLoadError):
            handler.load_file("nonexistent.inp")

    def test_get_junctions_without_load_raises(self):
        handler = SwmmInpHandler()
        with pytest.raises(ModelNotLoadedError):
            handler.get_junctions()

    def test_get_summary_not_loaded_empty_counts(self):
        handler = SwmmInpHandler()
        summary = handler.get_summary()
        assert summary["loaded"] is False


class TestSwmmRptHandler:
    """Test SwmmRptHandler class."""

    def test_handler_initialization(self):
        handler = SwmmRptHandler()
        assert handler is not None

    def test_is_loaded_false(self):
        handler = SwmmRptHandler()
        assert handler.is_loaded() is False

    def test_load_missing_file_raises(self):
        handler = SwmmRptHandler()
        with pytest.raises(FileLoadError):
            handler.load_file("nonexistent.rpt")

    def test_get_errors_without_load_raises(self):
        handler = SwmmRptHandler()
        with pytest.raises(ModelNotLoadedError):
            handler.get_errors()

    def test_export_not_implemented(self):
        handler = SwmmRptHandler()
        with pytest.raises(NotImplementedError):
            handler.export_to_database()


class TestSwmmOutHandler:
    """Test SwmmOutHandler class."""

    def test_export_database_not_implemented(self):
        handler = SwmmOutHandler()
        with pytest.raises(NotImplementedError):
            handler.export_to_database()
