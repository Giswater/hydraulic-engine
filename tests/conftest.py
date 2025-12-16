"""
This file is part of Hydraulic Engine
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

Pytest configuration and fixtures.
"""
# -*- coding: utf-8 -*-
import os
import pytest
from pathlib import Path


@pytest.fixture
def test_data_dir() -> Path:
    """Return the path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def sample_epanet_inp(test_data_dir: Path) -> Path:
    """Return path to sample EPANET INP file."""
    return test_data_dir / "sample_epanet.inp"


@pytest.fixture
def sample_swmm_inp(test_data_dir: Path) -> Path:
    """Return path to sample SWMM INP file."""
    return test_data_dir / "sample_swmm.inp"


@pytest.fixture
def sample_epanet_rpt(test_data_dir: Path) -> Path:
    """Return path to sample EPANET RPT file."""
    return test_data_dir / "sample_epanet.rpt"


@pytest.fixture
def sample_swmm_rpt(test_data_dir: Path) -> Path:
    """Return path to sample SWMM RPT file."""
    return test_data_dir / "sample_swmm.rpt"


@pytest.fixture
def temp_output_dir(tmp_path: Path) -> Path:
    """Return a temporary directory for test outputs."""
    output_dir = tmp_path / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir
