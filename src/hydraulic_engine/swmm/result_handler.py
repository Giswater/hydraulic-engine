"""
This file is part of Hydraulic Engine
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
import os
from typing import Optional

from ..utils import tools_log
from abc import ABC, abstractmethod


class SwmmResultHandler(ABC):
    """
    Handler for SWMM results.
    
    Provides functionality to read and parse SWMM simulation results.     
    """

    def __init__(self):
        self.result_path: Optional[str] = None
        self.result = None
        self.error_msg: Optional[str] = None

    def load_result(self, result_path: str) -> bool:
        """
        Read and parse a result file.
        
        :param result_path: Path to result file
        :return: True if successful
        """
        if not os.path.isfile(result_path):
            self.error_msg = f"File not found: {result_path}"
            tools_log.log_error(self.error_msg)
            return False

        try:
            from swmm_api import read_out_file
            from swmm_api import read_rpt_file

            self.result_path = result_path
            if result_path.endswith(".out"):
                self.result = read_out_file(result_path)
            elif result_path.endswith(".rpt"):
                self.result = read_rpt_file(result_path)
            else:
                self.error_msg = f"Unsupported file type: {result_path}"
                tools_log.log_error(self.error_msg)
                return False
            tools_log.log_info(f"Successfully read result file: {result_path}")
            return True

        except Exception as e:
            self.error_msg = str(e)
            tools_log.log_error(f"Error reading result file: {e}")
            return False

    def is_loaded(self) -> bool:
        """Check if a result file is loaded."""
        return self.result is not None

    @abstractmethod
    def export_to_database(self) -> bool:
        pass  #TODO: Implement export to database

    @abstractmethod
    def export_to_frost(self) -> bool:
        pass  #TODO: Implement export to frost
