"""
This file is part of Hydraulic Engine
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from ..utils import tools_log


class EpanetRunStatus(Enum):
    """EPANET simulation run status"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    NOT_RUN = "not_run"


@dataclass
class EpanetRunResult:
    """Result of an EPANET simulation run"""
    status: EpanetRunStatus = EpanetRunStatus.NOT_RUN
    inp_path: Optional[str] = None
    rpt_path: Optional[str] = None
    out_path: Optional[str] = None
    return_code: Optional[int] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_seconds: Optional[float] = None


class EpanetRunner:
    """
    Class for running EPANET simulations.
    
    Uses WNTR (Water Network Tool for Resilience) library.
    
    Example usage:
        runner = EpanetRunner()
        result = runner.run("model.inp")
        
        # Or with custom output paths
        result = runner.run(
            inp_path="model.inp",
            rpt_path="results.rpt"
        )
    """

    def __init__(self, epanet_exe_path: Optional[str] = None):
        """
        Initialize EPANET runner.
        
        :param epanet_exe_path: Path to EPANET executable (optional, uses wntr by default)
        """
        self.epanet_exe_path = epanet_exe_path
        self._progress_callback: Optional[Callable[[int, str], None]] = None

    def set_progress_callback(self, callback: Callable[[int, str], None]) -> None:
        """
        Set callback for progress updates.
        
        :param callback: Function(progress: int, message: str)
        """
        self._progress_callback = callback

    def _report_progress(self, progress: int, message: str) -> None:
        """Report progress if callback is set."""
        if self._progress_callback:
            self._progress_callback(progress, message)

    def run(
        self,
        inp_path: str,
        rpt_path: Optional[str] = None,
        out_path: Optional[str] = None
    ) -> EpanetRunResult:
        """
        Run EPANET simulation.
        
        :param inp_path: Path to INP file
        :param rpt_path: Path for RPT output (optional, derived from inp_path if not provided)
        :param out_path: Path for OUT binary output (optional)
        :return: EpanetRunResult with simulation results
        """
        result = EpanetRunResult(inp_path=inp_path)

        # Validate INP file exists
        if not os.path.isfile(inp_path):
            result.status = EpanetRunStatus.ERROR
            result.errors.append(f"INP file not found: {inp_path}")
            tools_log.log_error(f"INP file not found: {inp_path}")
            return result

        # Generate output paths if not provided
        inp_path_obj = Path(inp_path)
        base_path = inp_path_obj.parent / inp_path_obj.stem

        if rpt_path is None:
            rpt_path = str(base_path) + ".rpt"
        if out_path is None:
            out_path = str(base_path) + ".out"

        result.rpt_path = rpt_path
        result.out_path = out_path

        self._report_progress(10, "Starting EPANET simulation...")
        tools_log.log_info(f"Running EPANET simulation: {inp_path}")

        return self._run_with_wntr(result)

    def _run_with_wntr(self, result: EpanetRunResult) -> EpanetRunResult:
        """
        Run simulation using WNTR library.
        
        :param result: EpanetRunResult object to populate
        :return: Updated EpanetRunResult
        """
        import time
        start_time = time.time()

        try:
            import wntr

            self._report_progress(20, "Loading network model...")

            # Load the water network model
            wn = wntr.network.WaterNetworkModel(result.inp_path)

            self._report_progress(40, "Running hydraulic simulation...")

            # Create and run simulator
            sim = wntr.sim.EpanetSimulator(wn)
            results = sim.run_sim()

            self._report_progress(80, "Simulation completed, processing results...")

            # Store results summary
            result.duration_seconds = time.time() - start_time
            result.status = EpanetRunStatus.SUCCESS

            self._report_progress(100, f"Simulation finished: {result.status.value}")
            tools_log.log_info(f"EPANET simulation completed: {result.status.value} ({result.duration_seconds:.2f}s)")

        except ImportError as e:
            result.status = EpanetRunStatus.ERROR
            result.errors.append(f"wntr not installed: {e}")
            tools_log.log_error(f"wntr not installed: {e}")

        except Exception as e:
            result.status = EpanetRunStatus.ERROR
            result.errors.append(str(e))
            tools_log.log_error(f"EPANET simulation error: {e}")
            result.duration_seconds = time.time() - start_time

        return result

    def validate_inp(self, inp_path: str) -> Dict[str, Any]:
        """
        Validate an INP file without running simulation.
        
        :param inp_path: Path to INP file
        :return: Validation result dictionary
        """
        validation = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "info": {}
        }

        if not os.path.isfile(inp_path):
            validation["errors"].append(f"File not found: {inp_path}")
            return validation

        try:
            import wntr

            wn = wntr.network.WaterNetworkModel(inp_path)

            # Get basic info
            validation["info"]["name"] = wn.name
            validation["info"]["junctions"] = wn.num_junctions
            validation["info"]["tanks"] = wn.num_tanks
            validation["info"]["reservoirs"] = wn.num_reservoirs
            validation["info"]["pipes"] = wn.num_pipes
            validation["info"]["pumps"] = wn.num_pumps
            validation["info"]["valves"] = wn.num_valves

            validation["valid"] = True
            tools_log.log_info(f"INP validation successful: {inp_path}")

        except Exception as e:
            validation["errors"].append(str(e))
            tools_log.log_error(f"INP validation failed: {e}")

        return validation
