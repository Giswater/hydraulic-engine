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


class SwmmInpHandler:
    """
    Handler for SWMM INP files.
    
    Provides functionality to read, parse, and write SWMM INP files
    using the swmm-api library.
    
    Example usage:
        handler = SwmmInpHandler()
        handler.read("model.inp")
        
        # Get sections
        junctions = handler.get_junctions()
        conduits = handler.get_conduits()
        
        # Modify and save
        handler.write("modified_model.inp")
    """

    def __init__(self):
        self.inp_path: Optional[str] = None
        self.inp = None  # swmm_api SwmmInput object
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
            from swmm_api import read_inp_file

            self.inp_path = inp_path
            self.inp = read_inp_file(inp_path)
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
        if self.inp is None:
            self.error_msg = "No INP file loaded"
            return False

        try:
            path = output_path or self.inp_path
            self.inp.write_file(path)
            tools_log.log_info(f"Successfully wrote INP file: {path}")
            return True

        except Exception as e:
            self.error_msg = str(e)
            tools_log.log_error(f"Error writing INP file: {e}")
            return False

    def is_loaded(self) -> bool:
        """Check if an INP file is loaded."""
        return self.inp is not None

    # =========================================================================
    # Section Getters
    # =========================================================================

    def get_title(self) -> Optional[str]:
        """Get model title."""
        if not self.inp:
            return None
        return getattr(self.inp.TITLE, 'title', None) if hasattr(self.inp, 'TITLE') else None

    def get_options(self) -> Optional[Dict[str, Any]]:
        """Get OPTIONS section as dictionary."""
        if not self.inp or not hasattr(self.inp, 'OPTIONS'):
            return None
        try:
            return {k: v for k, v in vars(self.inp.OPTIONS).items() if not k.startswith('_')}
        except Exception:
            return None

    def get_junctions(self) -> Optional[Dict[str, Any]]:
        """
        Get JUNCTIONS section.
        
        :return: Dictionary of junctions {id: junction_data}
        """
        if not self.inp or not hasattr(self.inp, 'JUNCTIONS'):
            return None
        return dict(self.inp.JUNCTIONS)

    def get_outfalls(self) -> Optional[Dict[str, Any]]:
        """Get OUTFALLS section."""
        if not self.inp or not hasattr(self.inp, 'OUTFALLS'):
            return None
        return dict(self.inp.OUTFALLS)

    def get_storage(self) -> Optional[Dict[str, Any]]:
        """Get STORAGE section."""
        if not self.inp or not hasattr(self.inp, 'STORAGE'):
            return None
        return dict(self.inp.STORAGE)

    def get_dividers(self) -> Optional[Dict[str, Any]]:
        """Get DIVIDERS section."""
        if not self.inp or not hasattr(self.inp, 'DIVIDERS'):
            return None
        return dict(self.inp.DIVIDERS)

    def get_conduits(self) -> Optional[Dict[str, Any]]:
        """Get CONDUITS section."""
        if not self.inp or not hasattr(self.inp, 'CONDUITS'):
            return None
        return dict(self.inp.CONDUITS)

    def get_pumps(self) -> Optional[Dict[str, Any]]:
        """Get PUMPS section."""
        if not self.inp or not hasattr(self.inp, 'PUMPS'):
            return None
        return dict(self.inp.PUMPS)

    def get_orifices(self) -> Optional[Dict[str, Any]]:
        """Get ORIFICES section."""
        if not self.inp or not hasattr(self.inp, 'ORIFICES'):
            return None
        return dict(self.inp.ORIFICES)

    def get_weirs(self) -> Optional[Dict[str, Any]]:
        """Get WEIRS section."""
        if not self.inp or not hasattr(self.inp, 'WEIRS'):
            return None
        return dict(self.inp.WEIRS)

    def get_outlets(self) -> Optional[Dict[str, Any]]:
        """Get OUTLETS section."""
        if not self.inp or not hasattr(self.inp, 'OUTLETS'):
            return None
        return dict(self.inp.OUTLETS)

    def get_subcatchments(self) -> Optional[Dict[str, Any]]:
        """Get SUBCATCHMENTS section."""
        if not self.inp or not hasattr(self.inp, 'SUBCATCHMENTS'):
            return None
        return dict(self.inp.SUBCATCHMENTS)

    def get_subareas(self) -> Optional[Dict[str, Any]]:
        """Get SUBAREAS section."""
        if not self.inp or not hasattr(self.inp, 'SUBAREAS'):
            return None
        return dict(self.inp.SUBAREAS)

    def get_infiltration(self) -> Optional[Dict[str, Any]]:
        """Get INFILTRATION section."""
        if not self.inp or not hasattr(self.inp, 'INFILTRATION'):
            return None
        return dict(self.inp.INFILTRATION)

    def get_coordinates(self) -> Optional[Dict[str, tuple]]:
        """Get COORDINATES section."""
        if not self.inp or not hasattr(self.inp, 'COORDINATES'):
            return None
        return dict(self.inp.COORDINATES)

    def get_vertices(self) -> Optional[Dict[str, List[tuple]]]:
        """Get VERTICES section (link vertices)."""
        if not self.inp or not hasattr(self.inp, 'VERTICES'):
            return None
        return dict(self.inp.VERTICES)

    def get_polygons(self) -> Optional[Dict[str, List[tuple]]]:
        """Get POLYGONS section (subcatchment polygons)."""
        if not self.inp or not hasattr(self.inp, 'POLYGONS'):
            return None
        return dict(self.inp.POLYGONS)

    def get_xsections(self) -> Optional[Dict[str, Any]]:
        """Get XSECTIONS section."""
        if not self.inp or not hasattr(self.inp, 'XSECTIONS'):
            return None
        return dict(self.inp.XSECTIONS)

    def get_transects(self) -> Optional[Dict[str, Any]]:
        """Get TRANSECTS section."""
        if not self.inp or not hasattr(self.inp, 'TRANSECTS'):
            return None
        return dict(self.inp.TRANSECTS)

    def get_curves(self) -> Optional[Dict[str, Any]]:
        """Get CURVES section."""
        if not self.inp or not hasattr(self.inp, 'CURVES'):
            return None
        return dict(self.inp.CURVES)

    def get_timeseries(self) -> Optional[Dict[str, Any]]:
        """Get TIMESERIES section."""
        if not self.inp or not hasattr(self.inp, 'TIMESERIES'):
            return None
        return dict(self.inp.TIMESERIES)

    def get_patterns(self) -> Optional[Dict[str, Any]]:
        """Get PATTERNS section."""
        if not self.inp or not hasattr(self.inp, 'PATTERNS'):
            return None
        return dict(self.inp.PATTERNS)

    def get_raingages(self) -> Optional[Dict[str, Any]]:
        """Get RAINGAGES section."""
        if not self.inp or not hasattr(self.inp, 'RAINGAGES'):
            return None
        return dict(self.inp.RAINGAGES)

    def get_inflows(self) -> Optional[Dict[str, Any]]:
        """Get INFLOWS section."""
        if not self.inp or not hasattr(self.inp, 'INFLOWS'):
            return None
        return dict(self.inp.INFLOWS)

    def get_dwf(self) -> Optional[Dict[str, Any]]:
        """Get DWF (Dry Weather Flow) section."""
        if not self.inp or not hasattr(self.inp, 'DWF'):
            return None
        return dict(self.inp.DWF)

    # =========================================================================
    # Summary and Statistics
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the INP file contents.
        
        :return: Dictionary with counts of each element type
        """
        summary = {
            "file": self.inp_path,
            "loaded": self.is_loaded(),
            "title": self.get_title(),
            "counts": {}
        }

        if not self.inp:
            return summary

        sections = [
            ("junctions", "JUNCTIONS"),
            ("outfalls", "OUTFALLS"),
            ("storage", "STORAGE"),
            ("dividers", "DIVIDERS"),
            ("conduits", "CONDUITS"),
            ("pumps", "PUMPS"),
            ("orifices", "ORIFICES"),
            ("weirs", "WEIRS"),
            ("outlets", "OUTLETS"),
            ("subcatchments", "SUBCATCHMENTS"),
            ("raingages", "RAINGAGES"),
            ("curves", "CURVES"),
            ("timeseries", "TIMESERIES"),
            ("patterns", "PATTERNS"),
        ]

        for name, attr in sections:
            if hasattr(self.inp, attr):
                section = getattr(self.inp, attr)
                summary["counts"][name] = len(section) if section else 0
            else:
                summary["counts"][name] = 0

        return summary

    # =========================================================================
    # Raw INP Access
    # =========================================================================

    def get_raw_inp(self) -> Any:
        """
        Get the raw swmm_api SwmmInput object.
        
        :return: SwmmInput object or None
        """
        return self.inp

    def get_section(self, section_name: str) -> Optional[Any]:
        """
        Get any section by name.
        
        :param section_name: Section name (e.g., 'JUNCTIONS', 'CONDUITS')
        :return: Section data or None
        """
        if not self.inp:
            return None
        return getattr(self.inp, section_name.upper(), None)
