"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional

from .file_handler import SwmmResultHandler, SwmmFileHandler
from ..exceptions import ModelNotLoadedError, FileLoadError


def _require_rpt_loaded(handler: "SwmmRptHandler") -> Any:
    if handler.file_object is None:
        raise ModelNotLoadedError("No RPT file loaded")
    return handler.file_object


def _get_rpt_attr(handler: "SwmmRptHandler", attr_name: str) -> Optional[Any]:
    file_object = _require_rpt_loaded(handler)
    return getattr(file_object, attr_name, None)


class SwmmRptHandler(SwmmFileHandler, SwmmResultHandler):
    """
    Handler for SWMM RPT (report) files.
    
    Provides functionality to read and parse SWMM simulation results.
    
    Example usage:
        handler = SwmmRptHandler()
        handler.load_file("results.rpt")
        
        # Get results
        node_results = handler.get_node_results()
        link_results = handler.get_link_results()
        summary = handler.get_summary()
    """

    def export_to_database(self) -> bool:
        raise NotImplementedError("SWMM RPT export to database is not implemented")

    def export_to_frost(self) -> bool:
        raise NotImplementedError("SWMM RPT export to FROST is not implemented")

    # =========================================================================
    # Analysis Information
    # =========================================================================

    def get_analysis_options(self) -> Optional[Dict[str, Any]]:
        """Get analysis options used in simulation."""
        return _get_rpt_attr(self, 'analysis_options')

    def get_runoff_quantity_continuity(self) -> Optional[Dict[str, Any]]:
        """Get runoff quantity continuity results."""
        return _get_rpt_attr(self, 'runoff_quantity_continuity')

    def get_flow_routing_continuity(self) -> Optional[Dict[str, Any]]:
        """Get flow routing continuity results."""
        return _get_rpt_attr(self, 'flow_routing_continuity')

    # =========================================================================
    # Node Results
    # =========================================================================

    def get_node_depth_summary(self) -> Optional[Any]:
        """Get node depth summary."""
        return _get_rpt_attr(self, 'node_depth_summary')

    def get_node_inflow_summary(self) -> Optional[Any]:
        """Get node inflow summary."""
        return _get_rpt_attr(self, 'node_inflow_summary')

    def get_node_surcharge_summary(self) -> Optional[Any]:
        """Get node surcharge summary."""
        return _get_rpt_attr(self, 'node_surcharge_summary')

    def get_node_flooding_summary(self) -> Optional[Any]:
        """Get node flooding summary."""
        return _get_rpt_attr(self, 'node_flooding_summary')

    # =========================================================================
    # Link Results
    # =========================================================================

    def get_link_flow_summary(self) -> Optional[Any]:
        """Get link flow summary."""
        return _get_rpt_attr(self, 'link_flow_summary')

    def get_conduit_surcharge_summary(self) -> Optional[Any]:
        """Get conduit surcharge summary."""
        return _get_rpt_attr(self, 'conduit_surcharge_summary')

    def get_pumping_summary(self) -> Optional[Any]:
        """Get pumping summary."""
        return _get_rpt_attr(self, 'pumping_summary')

    # =========================================================================
    # Subcatchment Results
    # =========================================================================

    def get_subcatchment_runoff_summary(self) -> Optional[Any]:
        """Get subcatchment runoff summary."""
        return _get_rpt_attr(self, 'subcatchment_runoff_summary')

    # =========================================================================
    # Error and Warning Information
    # =========================================================================

    def get_errors(self) -> List[str]:
        """Get list of errors from report."""
        if not self.file_path:
            raise ModelNotLoadedError("No RPT file loaded")

        errors: List[str] = []
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if 'ERROR' in line.upper():
                        errors.append(line.strip())
        except OSError as e:
            raise FileLoadError(f"Could not read RPT file '{self.file_path}': {e}") from e
        return errors

    def get_warnings(self) -> List[str]:
        """Get list of warnings from report."""
        if not self.file_path:
            raise ModelNotLoadedError("No RPT file loaded")

        warnings: List[str] = []
        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if 'WARNING' in line.upper():
                        warnings.append(line.strip())
        except OSError as e:
            raise FileLoadError(f"Could not read RPT file '{self.file_path}': {e}") from e
        return warnings

    def was_successful(self) -> bool:
        """Check if the simulation was successful."""
        if not self.file_path:
            raise ModelNotLoadedError("No RPT file loaded")

        try:
            with open(self.file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return (
                    'Analysis begun' in content
                    and 'run was unsuccessful' not in content.lower()
                )
        except OSError as e:
            raise FileLoadError(f"Could not read RPT file '{self.file_path}': {e}") from e

    # =========================================================================
    # Summary
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the RPT file contents.
        
        :return: Dictionary with summary information
        """
        summary = {
            "file": self.file_path,
            "loaded": self.is_loaded(),
            "successful": self.was_successful() if self.is_loaded() else False,
            "errors": self.get_errors() if self.file_path else [],
            "warnings": self.get_warnings() if self.file_path else [],
            "has_node_depth_summary": self.get_node_depth_summary() is not None,
            "has_link_flow_summary": self.get_link_flow_summary() is not None,
            "has_subcatchment_runoff_summary": (
                self.get_subcatchment_runoff_summary() is not None
            ),
        }
        return summary

    # =========================================================================
    # Raw RPT Access
    # =========================================================================

    def get_raw_rpt(self) -> Any:
        """
        Get the raw swmm_api SwmmReport object.
        
        :return: SwmmReport object
        """
        return _require_rpt_loaded(self)

    def get_section(self, section_name: str) -> Optional[Any]:
        """
        Get any section by attribute name.
        
        :param section_name: Section attribute name
        :return: Section data or None if the section is not present
        """
        return _get_rpt_attr(self, section_name)
