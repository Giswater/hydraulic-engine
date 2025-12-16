"""
This file is part of Hydraulic Engine
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
from typing import Any, Dict, List, Optional

from ..utils import tools_log
from .result_handler import SwmmResultHandler


class SwmmRptHandler(SwmmResultHandler):
    """
    Handler for SWMM RPT (report) files.
    
    Provides functionality to read and parse SWMM simulation results.
    
    Example usage:
        handler = SwmmRptHandler()
        handler.load_result("results.rpt")
        
        # Get results
        node_results = handler.get_node_results()
        link_results = handler.get_link_results()
        summary = handler.get_summary()
    """

    def export_to_database(self) -> bool:
        pass  #TODO: Implement export to database

    # =========================================================================
    # Analysis Information
    # =========================================================================

    def get_analysis_options(self) -> Optional[Dict[str, Any]]:
        """Get analysis options used in simulation."""
        if not self.rpt:
            return None
        try:
            if hasattr(self.rpt, 'analysis_options'):
                return self.rpt.analysis_options
        except Exception:
            pass
        return None

    def get_runoff_quantity_continuity(self) -> Optional[Dict[str, Any]]:
        """Get runoff quantity continuity results."""
        if not self.rpt:
            return None
        try:
            if hasattr(self.rpt, 'runoff_quantity_continuity'):
                return self.rpt.runoff_quantity_continuity
        except Exception:
            pass
        return None

    def get_flow_routing_continuity(self) -> Optional[Dict[str, Any]]:
        """Get flow routing continuity results."""
        if not self.rpt:
            return None
        try:
            if hasattr(self.rpt, 'flow_routing_continuity'):
                return self.rpt.flow_routing_continuity
        except Exception:
            pass
        return None

    # =========================================================================
    # Node Results
    # =========================================================================

    def get_node_depth_summary(self) -> Optional[Any]:
        """Get node depth summary."""
        if not self.rpt:
            return None
        try:
            if hasattr(self.rpt, 'node_depth_summary'):
                return self.rpt.node_depth_summary
        except Exception:
            pass
        return None

    def get_node_inflow_summary(self) -> Optional[Any]:
        """Get node inflow summary."""
        if not self.rpt:
            return None
        try:
            if hasattr(self.rpt, 'node_inflow_summary'):
                return self.rpt.node_inflow_summary
        except Exception:
            pass
        return None

    def get_node_surcharge_summary(self) -> Optional[Any]:
        """Get node surcharge summary."""
        if not self.rpt:
            return None
        try:
            if hasattr(self.rpt, 'node_surcharge_summary'):
                return self.rpt.node_surcharge_summary
        except Exception:
            pass
        return None

    def get_node_flooding_summary(self) -> Optional[Any]:
        """Get node flooding summary."""
        if not self.rpt:
            return None
        try:
            if hasattr(self.rpt, 'node_flooding_summary'):
                return self.rpt.node_flooding_summary
        except Exception:
            pass
        return None

    # =========================================================================
    # Link Results
    # =========================================================================

    def get_link_flow_summary(self) -> Optional[Any]:
        """Get link flow summary."""
        if not self.rpt:
            return None
        try:
            if hasattr(self.rpt, 'link_flow_summary'):
                return self.rpt.link_flow_summary
        except Exception:
            pass
        return None

    def get_conduit_surcharge_summary(self) -> Optional[Any]:
        """Get conduit surcharge summary."""
        if not self.rpt:
            return None
        try:
            if hasattr(self.rpt, 'conduit_surcharge_summary'):
                return self.rpt.conduit_surcharge_summary
        except Exception:
            pass
        return None

    def get_pumping_summary(self) -> Optional[Any]:
        """Get pumping summary."""
        if not self.rpt:
            return None
        try:
            if hasattr(self.rpt, 'pumping_summary'):
                return self.rpt.pumping_summary
        except Exception:
            pass
        return None

    # =========================================================================
    # Subcatchment Results
    # =========================================================================

    def get_subcatchment_runoff_summary(self) -> Optional[Any]:
        """Get subcatchment runoff summary."""
        if not self.rpt:
            return None
        try:
            if hasattr(self.rpt, 'subcatchment_runoff_summary'):
                return self.rpt.subcatchment_runoff_summary
        except Exception:
            pass
        return None

    # =========================================================================
    # Error and Warning Information
    # =========================================================================

    def get_errors(self) -> List[str]:
        """Get list of errors from report."""
        errors = []
        if not self.rpt_path:
            return errors

        try:
            with open(self.rpt_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if 'ERROR' in line.upper():
                        errors.append(line.strip())
        except Exception:
            pass
        return errors

    def get_warnings(self) -> List[str]:
        """Get list of warnings from report."""
        warnings = []
        if not self.rpt_path:
            return warnings

        try:
            with open(self.rpt_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if 'WARNING' in line.upper():
                        warnings.append(line.strip())
        except Exception:
            pass
        return warnings

    def was_successful(self) -> bool:
        """Check if the simulation was successful."""
        if not self.rpt_path:
            return False

        try:
            with open(self.rpt_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return 'Analysis begun' in content and 'run was unsuccessful' not in content.lower()
        except Exception:
            return False

    # =========================================================================
    # Summary
    # =========================================================================

    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the RPT file contents.
        
        :return: Dictionary with summary information
        """
        summary = {
            "file": self.rpt_path,
            "loaded": self.is_loaded(),
            "successful": self.was_successful(),
            "errors": self.get_errors(),
            "warnings": self.get_warnings(),
            "has_node_depth_summary": self.get_node_depth_summary() is not None,
            "has_link_flow_summary": self.get_link_flow_summary() is not None,
            "has_subcatchment_runoff_summary": self.get_subcatchment_runoff_summary() is not None,
        }
        return summary

    # =========================================================================
    # Raw RPT Access
    # =========================================================================

    def get_raw_rpt(self) -> Any:
        """
        Get the raw swmm_api SwmmReport object.
        
        :return: SwmmReport object or None
        """
        return self.rpt

    def get_section(self, section_name: str) -> Optional[Any]:
        """
        Get any section by attribute name.
        
        :param section_name: Section attribute name
        :return: Section data or None
        """
        if not self.rpt:
            return None
        return getattr(self.rpt, section_name, None)
