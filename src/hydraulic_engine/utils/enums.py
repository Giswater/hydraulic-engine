"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
from enum import Enum


class RunStatus(Enum):
    """Simulation run status"""
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    NOT_RUN = "not_run"


class ExportDataSource(Enum):
    """Export data source"""
    DATABASE = "database"
    FROST = "frost"