"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

EPANET module tests.
"""
# -*- coding: utf-8 -*-
import pytest

from hydraulic_engine import FileLoadError, ModelNotLoadedError
from hydraulic_engine.epanet import EpanetRunner, EpanetInpHandler, EpanetBinHandler, EpanetRunResult
from hydraulic_engine.utils.enums import RunStatus


class TestEpanetImports:
    """Test EPANET module imports."""

    def test_import_from_package(self):
        from hydraulic_engine import epanet
        assert EpanetRunner is not None
        assert epanet.EpanetInpHandler is not None
        assert epanet.EpanetBinHandler is not None

    def test_import_exceptions_from_epanet(self):
        from hydraulic_engine.epanet import ModelNotLoadedError, ValidationError
        assert issubclass(ModelNotLoadedError, Exception)


class TestEpanetRunner:
    """Test EpanetRunner class."""

    def test_runner_initialization(self):
        runner = EpanetRunner(inp_path="model.inp")
        assert runner is not None

    def test_run_missing_file_raises(self):
        runner = EpanetRunner(inp_path="nonexistent.inp")
        with pytest.raises(FileLoadError):
            runner.run()


class TestEpanetInpHandler:
    """Test EpanetInpHandler class."""

    def test_handler_initialization(self):
        handler = EpanetInpHandler()
        assert handler is not None
        assert handler.file_path is None

    def test_is_loaded_false(self):
        handler = EpanetInpHandler()
        assert handler.is_loaded() is False

    def test_load_missing_file_raises(self):
        handler = EpanetInpHandler()
        with pytest.raises(FileLoadError):
            handler.load_file("nonexistent.inp")

    def test_get_summary_not_loaded(self):
        handler = EpanetInpHandler()
        with pytest.raises(ModelNotLoadedError):
            handler.get_title()

    def test_validate_missing_file_returns_invalid_dict(self):
        handler = EpanetInpHandler()
        handler.file_path = "nonexistent.inp"
        validation = handler.validate_inp()
        assert validation["valid"] is False
        assert len(validation["errors"]) > 0


class TestEpanetBinHandler:
    """Test EpanetBinHandler class."""

    def test_handler_initialization(self):
        handler = EpanetBinHandler()
        assert handler is not None
        assert handler.is_loaded() is False

    def test_export_without_bin_raises(self):
        from hydraulic_engine.exceptions import ModelNotLoadedError

        handler = EpanetBinHandler()
        inp = EpanetInpHandler()
        with pytest.raises(ModelNotLoadedError):
            handler.export_to_database(result_id="1", inp_handler=inp)
