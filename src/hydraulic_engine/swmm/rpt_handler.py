"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
import re

from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import pandas as pd

from .export_db import (
    FLOW_ROUTING_FIELDS,
    RUNOFF_QUANTITY_FIELDS,
    SUMMARY_TABLES,
    SUMMARY_TOPICS,
    build_continuity_row,
    build_summary_records,
    clean_result,
    copy_records,
    describe_tables,
    finalize_result,
    insert_row,
    truncate_text,
)
from .file_handler import SwmmResultHandler, SwmmFileHandler
from ..exceptions import DatabaseError, ExportError, ModelNotLoadedError, FileLoadError
from ..utils import tools_log
from ..utils.tools_db import HePgDao, get_connection


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

    def export_to_database(
            self,
            result_id: str,
            round_decimals: int = 4,
            dao: Optional[HePgDao] = None,
            commit: bool = True
        ) -> bool:
        """
        Export the RPT summaries to the Giswater database.

        The report only exposes aggregated sections, so this covers the maxima and
        the run diagnostics. Time series live in the OUT binary and are exported by
        :meth:`SwmmOutHandler.export_to_database` for the elements requested in the
        INP ``[REPORT]`` section.

        Fills the following tables:
        - rpt_nodedepth_sum, rpt_nodeinflow_sum, rpt_nodesurcharge_sum,
          rpt_nodeflooding_sum, rpt_storagevol_sum, rpt_outfallflow_sum: Node maxima
        - rpt_arcflow_sum, rpt_flowclass_sum, rpt_condsurcharge_sum,
          rpt_pumping_sum: Arc maxima
        - rpt_subcatchrunoff_sum, rpt_lidperformance_sum: Subcatchment maxima
        - rpt_runoff_quant, rpt_flowrouting_cont: Continuity balances
        - rpt_warning_summary and the diagnostic text tables
        - rpt_cat_result, selector_rpt_main: Result metadata and selection

        Sections the report does not contain are skipped instead of failing, since
        SWMM omits whole sections when nothing surcharged, flooded or overflowed.

        :param result_id: The result identifier (must match rpt_cat_result.result_id)
        :param round_decimals: Number of decimal places to round the results (default: 2)
        :param dao: Database access object (optional, uses global connection if not provided)
        :param commit: Commit and finalize the result. Set to False when the caller
            owns the transaction, as the runner does when the OUT export follows
        :return: True if export successful
        """
        report = _require_rpt_loaded(self)

        if dao is None:
            dao = get_connection()

        if dao is None or not dao.is_connected():
            raise DatabaseError("No database connection available")

        try:
            tools_log.log_info(f"Starting RPT summary export for result_id: {result_id}")

            described = describe_tables(dao, SUMMARY_TABLES)

            tools_log.log_info("Cleaning previous summary results...")
            clean_result(dao, result_id, SUMMARY_TABLES, described)

            tools_log.log_info("Inserting report summaries...")
            summary_count = _export_summaries(dao, report, result_id, round_decimals, described)
            tools_log.log_info(f"Inserted {summary_count} summary records")

            tools_log.log_info("Inserting continuity balances...")
            _export_continuity(dao, report, result_id, round_decimals, described)

            tools_log.log_info("Inserting warnings and diagnostics...")
            _export_diagnostics(dao, report, result_id, described)

            if commit:
                tools_log.log_info("Updating result catalog and selectors...")
                finalize_result(dao, result_id)
                dao.commit()

            tools_log.log_info(f"RPT summary export completed for result_id: {result_id}")
            return True

        except (DatabaseError, ExportError, ModelNotLoadedError):
            _rollback(dao, commit)
            raise
        except Exception as e:
            tools_log.log_error(f"Error exporting RPT summaries to database: {e}")
            _rollback(dao, commit)
            raise ExportError(f"Error exporting RPT summaries to database: {e}") from e

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


# region Export to database helper functions

# Diagnostic sections stored as free text by Giswater. The element flag selects
# between "label (value)" element listings and "key: value" summary lines.
_DIAGNOSTIC_TOPICS: Tuple[Tuple[str, str, bool], ...] = (
    ('highest_continuity_errors', 'rpt_high_conterrors', True),
    ('time_step_critical_elements', 'rpt_timestep_critelem', True),
    ('highest_flow_instability_indexes', 'rpt_high_flowinest_ind', True),
    ('routing_time_step_summary', 'rpt_routing_timestep', False),
)

_WARNING_NUMBER = re.compile(r'(WARNING\s*\d+)')


def _rollback(dao: HePgDao, owns_transaction: bool) -> None:
    """Roll back the transaction when this export opened it."""
    if not owns_transaction:
        return
    try:
        dao.rollback()
    except DatabaseError:
        pass


def _section(report: Any, attr: str) -> Optional[Any]:
    """
    Read a report section, treating parse failures as a missing section.

    swmm_api parses sections lazily, so a malformed block raises on attribute
    access. One unusable section should not abort the whole export.

    :param report: swmm_api SwmmReport object
    :param attr: Section attribute name
    :return: Section data or None
    """
    try:
        return getattr(report, attr, None)
    except Exception as e:
        tools_log.log_warning(f"Could not read RPT section '{attr}': {e}")
        return None


def _restrict(row: Dict[str, Any], allowed_columns: Set[str]) -> Dict[str, Any]:
    """Drop mapped columns the target table does not have."""
    return {column: value for column, value in row.items() if column in allowed_columns}


def _export_summaries(
    dao: HePgDao,
    report: Any,
    result_id: str,
    round_decimals: int,
    described: Dict[str, Set[str]],
) -> int:
    """
    Copy every available report summary into its Giswater table.

    :param dao: Database access object
    :param report: swmm_api SwmmReport object
    :param result_id: Result identifier
    :param round_decimals: Decimal places to round numeric values to
    :param described: Inventory of existing tables and their columns
    :return: Total number of rows inserted
    """
    total = 0
    for topic in SUMMARY_TOPICS:
        allowed_columns = described.get(topic.table)
        if allowed_columns is None:
            tools_log.log_warning(f"Table {topic.table} not found in target schema, skipping")
            continue

        frame = _section(report, topic.attr)
        if frame is None or getattr(frame, 'empty', True):
            continue

        columns, records = build_summary_records(
            frame, result_id, topic, round_decimals, allowed_columns
        )
        count = copy_records(dao, topic.table, columns, records)
        total += count
        tools_log.log_info(f"Inserted {count} rows into {topic.table}")

    return total


def _export_continuity(
    dao: HePgDao,
    report: Any,
    result_id: str,
    round_decimals: int,
    described: Dict[str, Set[str]],
) -> None:
    """
    Insert the runoff quantity and flow routing continuity balances.

    :param dao: Database access object
    :param report: swmm_api SwmmReport object
    :param result_id: Result identifier
    :param round_decimals: Decimal places to round numeric values to
    :param described: Inventory of existing tables and their columns
    """
    continuity_targets = (
        ('runoff_quantity_continuity', 'rpt_runoff_quant', RUNOFF_QUANTITY_FIELDS),
        ('flow_routing_continuity', 'rpt_flowrouting_cont', FLOW_ROUTING_FIELDS),
    )

    for attr, table, fields in continuity_targets:
        allowed_columns = described.get(table)
        if allowed_columns is None:
            continue

        row = build_continuity_row(_section(report, attr), fields, round_decimals)
        if not row:
            continue

        insert_row(dao, table, {'result_id': result_id, **_restrict(row, allowed_columns)})
        tools_log.log_info(f"Inserted continuity balance into {table}")


def _diagnostic_value(value: Any) -> str:
    """
    Render a diagnostic value the way the report prints it.

    swmm_api turns the time-step lines into Timedelta objects, whose repr
    (``0 days 00:00:29.500000``) is far less readable than the report's own
    ``29.50 sec``, so durations are converted back to seconds.

    :param value: Parsed value
    :return: Display text
    """
    if isinstance(value, pd.Timedelta):
        return f"{value.total_seconds():.2f} sec"
    return str(value).strip()


def _diagnostic_lines(section: Any, is_element_listing: bool) -> List[str]:
    """
    Render a diagnostic section as the free-text lines Giswater stores.

    :param section: Parsed section, a dict of entries or a list of lines
    :param is_element_listing: True for element listings, False for summary lines
    :return: Text lines
    """
    if not section:
        return []
    if isinstance(section, (list, tuple)):
        return [str(line).strip() for line in section if str(line).strip()]
    if not isinstance(section, dict):
        return [str(section).strip()]

    separator = ' ({})' if is_element_listing else ': {}'
    return [
        f"{key}{separator.format(_diagnostic_value(value))}"
        for key, value in section.items()
    ]


def _iter_warning_rows(report: Any, result_id: str) -> Iterator[Tuple[Any, ...]]:
    """
    Build rpt_warning_summary rows from the report warnings.

    swmm_api groups warnings by message and lists the affected elements, so the
    numeric code is recovered from the message text.

    :param report: swmm_api SwmmReport object
    :param result_id: Result identifier
    :return: Row iterator
    """
    try:
        warnings = report.get_warnings() or {}
    except Exception as e:
        tools_log.log_warning(f"Could not read RPT warnings: {e}")
        return

    for message, elements in warnings.items():
        match = _WARNING_NUMBER.match(str(message))
        number = truncate_text(match.group(1) if match else message, 30)
        text = str(message)
        if isinstance(elements, (list, tuple, set)):
            labels = ', '.join(str(element) for element in elements)
            if labels:
                text = f"{text} {labels}"
        yield (result_id, number, text)


def _export_diagnostics(
    dao: HePgDao,
    report: Any,
    result_id: str,
    described: Dict[str, Set[str]],
) -> None:
    """
    Insert warnings, control actions and the diagnostic text sections.

    :param dao: Database access object
    :param report: swmm_api SwmmReport object
    :param result_id: Result identifier
    :param described: Inventory of existing tables and their columns
    """
    if 'rpt_warning_summary' in described:
        rows = list(_iter_warning_rows(report, result_id))
        if rows:
            count = copy_records(
                dao, 'rpt_warning_summary', ('result_id', 'warning_number', 'text'), rows
            )
            tools_log.log_info(f"Inserted {count} rows into rpt_warning_summary")

    text_targets = _DIAGNOSTIC_TOPICS + (('control_actions_taken', 'rpt_control_actions_taken', True),)
    for attr, table, is_element_listing in text_targets:
        if table not in described:
            continue

        lines = _diagnostic_lines(_section(report, attr), is_element_listing)
        if not lines:
            continue

        records = ((result_id, truncate_text(line, 255)) for line in lines)
        count = copy_records(dao, table, ('result_id', 'text'), records)
        tools_log.log_info(f"Inserted {count} rows into {table}")

# endregion
