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


class EpanetRptHandler:
    """
    Handler for EPANET RPT (report) files.
    
    Provides functionality to read and parse EPANET simulation results.
    
    Example usage:
        handler = EpanetRptHandler()
        handler.read("results.rpt")
        
        # Get results
        summary = handler.get_summary()
        errors = handler.get_errors()
    """

    def __init__(self):
        self.rpt_path: Optional[str] = None
        self.content: Optional[str] = None
        self.error_msg: Optional[str] = None

    def read(self, rpt_path: str) -> bool:
        """
        Read a RPT file.
        
        :param rpt_path: Path to RPT file
        :return: True if successful
        """
        if not os.path.isfile(rpt_path):
            self.error_msg = f"File not found: {rpt_path}"
            tools_log.log_error(self.error_msg)
            return False

        try:
            self.rpt_path = rpt_path
            with open(rpt_path, 'r', encoding='utf-8', errors='ignore') as f:
                self.content = f.read()
            tools_log.log_info(f"Successfully read RPT file: {rpt_path}")
            return True

        except Exception as e:
            self.error_msg = str(e)
            tools_log.log_error(f"Error reading RPT file: {e}")
            return False

    def is_loaded(self) -> bool:
        """Check if a RPT file is loaded."""
        return self.content is not None

    # =========================================================================
    # Error and Warning Information
    # =========================================================================

    def get_errors(self) -> List[str]:
        """Get list of errors from report."""
        errors = []
        if not self.content:
            return errors

        for line in self.content.split('\n'):
            if 'ERROR' in line.upper() or 'Error' in line:
                errors.append(line.strip())
        return errors

    def get_warnings(self) -> List[str]:
        """Get list of warnings from report."""
        warnings = []
        if not self.content:
            return warnings

        for line in self.content.split('\n'):
            if 'WARNING' in line.upper() or 'Warning' in line:
                warnings.append(line.strip())
        return warnings

    def was_successful(self) -> bool:
        """Check if the simulation was successful."""
        if not self.content:
            return False
        return 'Analysis begun' in self.content and 'ERROR' not in self.content.upper()

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
        }
        return summary

    def get_raw_content(self) -> Optional[str]:
        """
        Get the raw file content.
        
        :return: File content or None
        """
        return self.content
