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
from .result_handler import SwmmResultHandler


class SwmmOutHandler(SwmmResultHandler):
    """
    Handler for SWMM OUT (output) files.
    
    Provides functionality to read and parse SWMM simulation output.
    
    Example usage:
        handler = SwmmOutHandler()
        handler.load_result("results.out")        
    """

    def export_to_frost(self) -> bool:
        pass  #TODO: Implement export to frost

    #TODO: Add getters for the OUT file