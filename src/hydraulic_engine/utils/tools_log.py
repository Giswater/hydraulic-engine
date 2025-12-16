"""
This file is part of Hydraulic Engine
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
import logging
import inspect
import os
import time
from typing import Optional

from ..config import config
from . import tools_os


class HeLogger:
    """
    Logger class for Hydraulic Engine package.
    Handles file logging with configurable levels and formatting.
    """

    def __init__(
        self,
        log_name: str,
        log_level: int,
        log_suffix: str,
        folder_has_tstamp: bool = False,
        file_has_tstamp: bool = True,
        remove_previous: bool = False
    ):
        # Create logger
        self.logger_file = logging.getLogger(log_name)
        self.logger_file.setLevel(int(log_level))
        self.min_log_level = int(log_level)
        self.log_limit_characters: Optional[int] = None

        # Define log folder in users folder
        main_folder = os.path.join(tools_os.get_datadir(), config.user_folder_dir or "hydraulic_engine")
        log_folder = f"{main_folder}{os.sep}log{os.sep}"
        if folder_has_tstamp:
            tstamp = str(time.strftime(log_suffix))
            log_folder += tstamp + os.sep
        if not os.path.exists(log_folder):
            os.makedirs(log_folder)

        # Define filename
        filepath = log_folder + log_name
        if file_has_tstamp:
            tstamp = str(time.strftime(log_suffix))
            filepath += "_" + tstamp
        filepath += ".log"

        if remove_previous and os.path.exists(filepath):
            os.remove(filepath)
        self.filepath = filepath

        # Initialize number of errors in current process
        self.num_errors = 0

        # Add file handler
        self.add_file_handler()

    def set_logger_parameters(
        self,
        min_log_level: int,
        log_limit_characters: Optional[int] = None
    ) -> None:
        """Set logger parameters min_log_level and log_limit_characters"""
        try:
            self.min_log_level = int(min_log_level)
        except (ValueError, TypeError):
            pass

        if log_limit_characters is not None:
            try:
                self.log_limit_characters = int(log_limit_characters)
            except (ValueError, TypeError):
                pass

    def add_file_handler(self) -> None:
        """Add file handler to logger"""
        log_format = '%(asctime)s [%(levelname)s] - %(message)s\n'
        log_date = '%d/%m/%Y %H:%M:%S'
        formatter = logging.Formatter(log_format, log_date)
        self.fh = logging.FileHandler(self.filepath)
        self.fh.setFormatter(formatter)
        self.logger_file.addHandler(self.fh)

    def close_logger(self) -> None:
        """Remove file handler and close logger"""
        try:
            self.logger_file.removeHandler(self.fh)
            self.fh.flush()
            self.fh.close()
            del self.fh
        except Exception:
            pass

    def debug(self, msg: Optional[str] = None, stack_level: int = 2, stack_level_increase: int = 0) -> None:
        """Log message with level DEBUG (10)"""
        self._log(msg, logging.DEBUG, stack_level + stack_level_increase + 1)

    def info(self, msg: Optional[str] = None, stack_level: int = 2, stack_level_increase: int = 0) -> None:
        """Log message with level INFO (20)"""
        self._log(msg, logging.INFO, stack_level + stack_level_increase + 1)

    def warning(self, msg: Optional[str] = None, stack_level: int = 2, stack_level_increase: int = 0, sum_error: bool = True) -> None:
        """Log message with level WARNING (30)"""
        self._log(msg, logging.WARNING, stack_level + stack_level_increase + 1)
        if sum_error:
            self.num_errors += 1

    def error(self, msg: Optional[str] = None, stack_level: int = 2, stack_level_increase: int = 0, sum_error: bool = True) -> None:
        """Log message with level ERROR (40)"""
        self._log(msg, logging.ERROR, stack_level + stack_level_increase + 1)
        if sum_error:
            self.num_errors += 1

    def critical(self, msg: Optional[str] = None, stack_level: int = 2, stack_level_increase: int = 0, sum_error: bool = True) -> None:
        """Log message with level CRITICAL (50)"""
        self._log(msg, logging.CRITICAL, stack_level + stack_level_increase + 1)
        if sum_error:
            self.num_errors += 1

    def _log(self, msg: Optional[str] = None, log_level: int = logging.INFO, stack_level: int = 2) -> None:
        """Log message with selected level"""
        try:
            # Check session parameter 'min_log_level'
            if log_level < self.min_log_level:
                return

            if stack_level >= len(inspect.stack()):
                stack_level = len(inspect.stack()) - 1
            module_path = inspect.stack()[stack_level][1]
            file_name = os.path.basename(module_path)
            function_line = inspect.stack()[stack_level][2]
            function_name = inspect.stack()[stack_level][3]
            header = "{" + file_name + " | Line " + str(function_line) + " (" + str(function_name) + ")}"
            text = header
            if msg:
                if self.log_limit_characters and len(msg) > int(self.log_limit_characters):
                    msg = msg[:int(self.log_limit_characters)]
                text += f"\n{msg}"
            self.logger_file.log(log_level, text)

        except Exception as e:
            print(f"Error logging: {e}")


def set_logger(logger_name: str, min_log_level: int = 20) -> None:
    """
    Set logger class. This will generate a new logger file.

    :param logger_name: Name for the logger
    :param min_log_level: Minimum log level (default: 20 = INFO)
    """
    if config.logger is None:
        log_suffix = '%Y%m%d'
        config.logger = HeLogger(logger_name, min_log_level, str(log_suffix))


def log_debug(text: Optional[str] = None, logger_file: bool = True, stack_level_increase: int = 0) -> None:
    """Write debug message to log file"""
    if config.logger and logger_file:
        config.logger.debug(text, stack_level_increase=stack_level_increase)


def log_info(text: Optional[str] = None, logger_file: bool = True, stack_level_increase: int = 0) -> None:
    """Write info message to log file"""
    if config.logger and logger_file:
        config.logger.info(text, stack_level_increase=stack_level_increase)


def log_warning(text: Optional[str] = None, logger_file: bool = True, stack_level_increase: int = 0) -> None:
    """Write warning message to log file"""
    if config.logger and logger_file:
        config.logger.warning(text, stack_level_increase=stack_level_increase)


def log_error(text: Optional[str] = None, logger_file: bool = True, stack_level_increase: int = 0) -> None:
    """Write error message to log file"""
    if config.logger and logger_file:
        config.logger.error(text, stack_level_increase=stack_level_increase)
