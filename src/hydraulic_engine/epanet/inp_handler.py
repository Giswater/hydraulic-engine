"""
This file is part of Hydraulic Engine
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
import os
from typing import Any, Dict, List, Optional

from ..utils import tools_log


class EpanetInpHandler:
    """
    Handler for EPANET INP files.
    
    Provides functionality to read, parse, and write EPANET INP files
    using the WNTR library.
    
    Example usage:
        handler = EpanetInpHandler()
        handler.read("model.inp")
        
        # Get network elements
        junctions = handler.get_junctions()
        pipes = handler.get_pipes()
        
        # Modify and save
        handler.write("modified_model.inp")
    """

    def __init__(self):
        self.inp_path: Optional[str] = None
        self.wn = None  # wntr WaterNetworkModel object
        self.error_msg: Optional[str] = None

    def read(self, inp_path: str) -> bool:
        """
        Read and parse an INP file.
        
        :param inp_path: Path to INP file
        :return: True if successful
        """
        if not os.path.isfile(inp_path):
            self.error_msg = f"File not found: {inp_path}"
            tools_log.log_error(self.error_msg)
            return False

        try:
            import wntr

            self.inp_path = inp_path
            self.wn = wntr.network.WaterNetworkModel(inp_path)
            tools_log.log_info(f"Successfully read INP file: {inp_path}")
            return True

        except Exception as e:
            self.error_msg = str(e)
            tools_log.log_error(f"Error reading INP file: {e}")
            return False

    def write(self, output_path: Optional[str] = None) -> bool:
        """
        Write INP file to disk.
        
        :param output_path: Output path (uses original path if not provided)
        :return: True if successful
        """
        if self.wn is None:
            self.error_msg = "No INP file loaded"
            return False

        try:
            import wntr

            path = output_path or self.inp_path
            wntr.network.write_inpfile(self.wn, path)
            tools_log.log_info(f"Successfully wrote INP file: {path}")
            return True

        except Exception as e:
            self.error_msg = str(e)
            tools_log.log_error(f"Error writing INP file: {e}")
            return False

    def is_loaded(self) -> bool:
        """Check if an INP file is loaded."""
        return self.wn is not None

    # =========================================================================
    # Node Getters
    # =========================================================================

    def get_junctions(self) -> Optional[Dict[str, Any]]:
        """Get JUNCTIONS as dictionary."""
        if not self.wn:
            return None
        try:
            return {name: junction for name, junction in self.wn.junctions()}
        except Exception:
            return None

    def get_tanks(self) -> Optional[Dict[str, Any]]:
        """Get TANKS as dictionary."""
        if not self.wn:
            return None
        try:
            return {name: tank for name, tank in self.wn.tanks()}
        except Exception:
            return None

    def get_reservoirs(self) -> Optional[Dict[str, Any]]:
        """Get RESERVOIRS as dictionary."""
        if not self.wn:
            return None
        try:
            return {name: reservoir for name, reservoir in self.wn.reservoirs()}
        except Exception:
            return None

    # =========================================================================
    # Link Getters
    # =========================================================================

    def get_pipes(self) -> Optional[Dict[str, Any]]:
        """Get PIPES as dictionary."""
        if not self.wn:
            return None
        try:
            return {name: pipe for name, pipe in self.wn.pipes()}
        except Exception:
            return None

    def get_pumps(self) -> Optional[Dict[str, Any]]:
        """Get PUMPS as dictionary."""
        if not self.wn:
            return None
        try:
            return {name: pump for name, pump in self.wn.pumps()}
        except Exception:
            return None

    def get_valves(self) -> Optional[Dict[str, Any]]:
        """Get VALVES as dictionary."""
        if not self.wn:
            return None
        try:
            return {name: valve for name, valve in self.wn.valves()}
        except Exception:
            return None

    # =========================================================================
    # Other Getters
    # =========================================================================

    def get_patterns(self) -> Optional[Dict[str, Any]]:
        """Get PATTERNS as dictionary."""
        if not self.wn:
            return None
        try:
            return {name: pattern for name, pattern in self.wn.patterns()}
        except Exception:
            return None

    def get_curves(self) -> Optional[Dict[str, Any]]:
        """Get CURVES as dictionary."""
        if not self.wn:
            return None
        try:
            return {name: curve for name, curve in self.wn.curves()}
        except Exception:
            return None

    def get_controls(self) -> Optional[List[Any]]:
        """Get CONTROLS as list."""
        if not self.wn:
            return None
        try:
            return list(self.wn.controls())
        except Exception:
            return None

    # =========================================================================
    # Options and Times
    # =========================================================================

    def get_options(self) -> Optional[Dict[str, Any]]:
        """Get simulation OPTIONS."""
        if not self.wn:
            return None
        try:
            return {
                "hydraulic_timestep": self.wn.options.time.hydraulic_timestep,
                "quality_timestep": self.wn.options.time.quality_timestep,
                "duration": self.wn.options.time.duration,
                "headloss": self.wn.options.hydraulic.headloss,
                "viscosity": self.wn.options.hydraulic.viscosity,
            }
        except Exception:
            return None

    # =========================================================================
    # Summary
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the INP file contents.
        
        :return: Dictionary with counts of each element type
        """
        summary = {
            "file": self.inp_path,
            "loaded": self.is_loaded(),
            "name": None,
            "counts": {}
        }

        if not self.wn:
            return summary

        summary["name"] = self.wn.name
        summary["counts"] = {
            "junctions": self.wn.num_junctions,
            "tanks": self.wn.num_tanks,
            "reservoirs": self.wn.num_reservoirs,
            "pipes": self.wn.num_pipes,
            "pumps": self.wn.num_pumps,
            "valves": self.wn.num_valves,
            "patterns": self.wn.num_patterns,
            "curves": self.wn.num_curves,
        }

        return summary

    # =========================================================================
    # Raw Access
    # =========================================================================

    def get_raw_wn(self) -> Any:
        """
        Get the raw wntr WaterNetworkModel object.
        
        :return: WaterNetworkModel object or None
        """
        return self.wn
