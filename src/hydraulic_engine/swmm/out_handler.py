"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Sequence, Set, Tuple
from datetime import datetime, timezone

import numpy as np
import pandas as pd
from pyproj import Transformer
from swmm_api.output_file import SwmmOutput
from swmm_api.output_file.definitions import OBJECTS
from swmm_api.input_file import SwmmInput
from swmm_api.input_file.section_labels import COORDINATES, VERTICES

from .export_db import (
    TIMESERIES_TABLES,
    ReportElementSelection,
    ReportKindSelection,
    clean_result,
    copy_records,
    describe_tables,
    filter_labels_by_selection,
    finalize_result,
    truncate_text,
)
from .file_handler import SwmmResultHandler, SwmmFileHandler
from .inp_handler import SwmmInpHandler
from ..utils import tools_log
from ..utils.tools_api import get_api_client, HeFrostClient
from ..utils import tools_sensorthings
from ..utils.tools_db import HePgDao, get_connection
from ..exceptions import (
    ModelNotLoadedError,
    APIError,
    DatabaseError,
    ExportError,
    ValidationError,
)


class SwmmOutHandler(SwmmFileHandler, SwmmResultHandler):
    """
    Handler for SWMM OUT (output) files.

    Provides functionality to read and parse SWMM simulation output.

    Note: This module uses private helper functions (_prepare_*)
    for data preparation tasks. These are not part of the public API.

    Example usage:
        handler = SwmmOutHandler()
        handler.load_file("results.out")
        handler.export_to_frost(inp_handler=inp_handler, result_id="test1")
    """

    def export_to_database(
            self,
            result_id: str,
            round_decimals: int = 4,
            dao: Optional[HePgDao] = None,
            commit: bool = True,
            report_selection: Optional[ReportElementSelection] = None,
        ) -> bool:
        """
        Export the OUT time series to the Giswater database.

        The binary output is the only complete source of time series. Which
        elements are written is controlled by the INP ``[REPORT]`` section:
        ``ALL`` exports every label of that kind, an ID list exports only those
        IDs, and ``NONE``/absent skips the kind.

        Fills the following tables when selected:
        - rpt_node: Node time series (flooding, depth, head, inflow)
        - rpt_arc: Arc time series (flow, velocity, fullpercent)
        - rpt_subcatchment: Subcatchment time series (precip, losses, runoff)

        :param result_id: The result identifier (must match rpt_cat_result.result_id)
        :param round_decimals: Number of decimal places to round the results (default: 2)
        :param dao: Database access object (optional, uses global connection if not provided)
        :param commit: Commit and finalize the result. Set to False when the caller
            owns the transaction, as the runner does when combining RPT and OUT
        :param report_selection: Elements to export from ``[REPORT]``. Defaults to
            skipping every kind when not provided
        :return: True if export successful
        """
        if not self.is_loaded():
            raise ModelNotLoadedError("No OUT file loaded")

        if dao is None:
            dao = get_connection()

        if dao is None or not dao.is_connected():
            raise DatabaseError("No database connection available")

        results: SwmmOutput = self.file_object
        selection = report_selection or ReportElementSelection()

        try:
            tools_log.log_info(f"Starting OUT time series export for result_id: {result_id}")

            described = describe_tables(dao, TIMESERIES_TABLES)

            tools_log.log_info("Cleaning previous time series results...")
            clean_result(dao, result_id, TIMESERIES_TABLES, described)

            total = 0
            for topic in _TIMESERIES_TOPICS:
                allowed_columns = described.get(topic.table)
                if allowed_columns is None:
                    tools_log.log_warning(
                        f"Table {topic.table} not found in target schema, skipping"
                    )
                    continue

                kind_selection = selection.for_kind(topic.kind)
                if kind_selection is None:
                    tools_log.log_info(
                        f"Skipping {topic.table}: [REPORT] does not request {topic.kind}s"
                    )
                    continue

                total += _export_timeseries(
                    dao,
                    results,
                    result_id,
                    topic,
                    round_decimals,
                    allowed_columns,
                    kind_selection,
                )

            tools_log.log_info(f"Inserted {total} time series records")

            if commit:
                tools_log.log_info("Updating result catalog and selectors...")
                finalize_result(dao, result_id)
                dao.commit()

            tools_log.log_info(f"OUT time series export completed for result_id: {result_id}")
            return True

        except (DatabaseError, ExportError, ModelNotLoadedError):
            _rollback(dao, commit)
            raise
        except Exception as e:
            tools_log.log_error(f"Error exporting OUT time series to database: {e}")
            _rollback(dao, commit)
            raise ExportError(f"Error exporting OUT time series to database: {e}") from e


# region Export to FROST-Server

    def export_to_frost(
        self,
        inp_handler: SwmmInpHandler,
        result_id: str,
        batch_size: int = 50,
        max_workers: int = 4,
        crs_from: int = 25831,
        crs_to: int = 4326,
        client: Optional[HeFrostClient] = None
    ) -> bool:
        """
        Export simulation results to FROST-Server (SensorThings API).

        Creates Things for nodes and links, Datastreams for each output variable,
        and Observations for the time series data.

        :param inp_handler: INP handler to get coordinates
        :param result_id: ID of the result
        :param batch_size: Number of operations per batch (default 50, keep low for deep inserts)
        :param max_workers: Number of concurrent batch requests (default 4)
        :param crs_from: CRS of the input file
        :param crs_to: CRS of the output file
        :param client: FROST client (uses default if None)
        :return: True if successful
        """
        if client is None:
            client = get_api_client()

        if not client or not isinstance(client, HeFrostClient):
            raise APIError("No FROST client available")

        if not self.is_loaded():
            raise ModelNotLoadedError("No OUT file loaded")

        # Delete all existing entities. Note: This is only used for testing purposes.
        # if delete_all:
        #     tools_log.log_info("Deleting all existing entities...")
        #     tools_sensorthings.delete_all_entities(
        #         batch_size=batch_size,
        #         max_workers=max_workers,
        #         client=client
        #     )
        #     tools_log.log_info("Cleanup completed.")

        # Check if INP file is loaded
        if not inp_handler.is_loaded():
            raise ModelNotLoadedError("No INP file loaded")

        # Pre-fetch existing entities (optimized: 2 API calls instead of N)
        tools_log.log_info("Fetching existing entities from server...")
        things_cache = tools_sensorthings.get_all_things_with_locations(client)
        obs_props_cache = tools_sensorthings.get_all_observed_properties(client)
        tools_log.log_info(f"Found {len(things_cache)} existing Things and {len(obs_props_cache)} ObservedProperties")

        # Get or create ObservedProperties (only creates missing ones)
        property_ids = tools_sensorthings.get_or_create_observed_properties(
            obs_props_cache=obs_props_cache,
            engine='swmm',
            client=client
        )

        # Create new Sensor for this simulation run
        sensor_ids = tools_sensorthings.create_simulation_sensor(
            result_id=result_id,
            network_type='SWMM',
            inp_file=inp_handler.file_path,
            client=client
        )

        # Set up coordinate transformer
        transformer = Transformer.from_crs(crs_from, crs_to, always_xy=True)

        # Track feature IDs from the INP file
        inp_feature_ids = set()

        # Prepare node and link data
        tools_log.log_info("Preparing nodes...")
        nodes_data = _prepare_nodes_data(inp_handler.file_object)
        tools_log.log_info(f"Found {len(nodes_data)} nodes")

        node_things = _prepare_nodes_things_data(
            nodes_data, self.file_object, sensor_ids, property_ids,
            transformer, inp_feature_ids
        )

        tools_log.log_info("Preparing links...")
        links_data = _prepare_links_data(inp_handler.file_object)
        tools_log.log_info(f"Found {len(links_data)} links")

        link_things = _prepare_links_things_data(
            links_data, self.file_object, sensor_ids, property_ids,
            inp_handler.file_object, transformer, inp_feature_ids
        )

        # Combine all Things and process in batches
        all_things = node_things + link_things
        tools_log.log_info(
            f"Processing {len(all_things)} Things using batch requests "
            f"(batch_size={batch_size}, max_workers={max_workers})..."
        )
        tools_sensorthings.process_things_batch(
            all_things,
            things_cache,
            batch_size=batch_size,
            max_workers=max_workers,
            client=client
        )

        # Mark Things not in INP as obsolete
        tools_log.log_info("Checking for obsolete Things...")
        tools_sensorthings.mark_obsolete_things(
            things_cache,
            inp_feature_ids,
            batch_size=batch_size,
            max_workers=max_workers,
            client=client
        )

        tools_log.log_info("Processing completed!")
        return True

# endregion

# region Export to database helper functions


@dataclass(frozen=True)
class _SeriesField:
    """
    One Giswater column fed from OUT result variables.

    :param column: Target column in the Giswater table
    :param variables: OUT variable names, summed when more than one is given
    :param scale: Factor applied to the summed values
    """
    column: str
    variables: Tuple[str, ...]
    scale: float = 1.0


@dataclass(frozen=True)
class _TimeseriesTopic:
    """
    Mapping between an OUT object kind and a Giswater time-series table.

    :param kind: OUT object kind
    :param table: Target Giswater table
    :param id_column: Column receiving the element label
    :param id_length: Maximum width of the id column
    :param fields: Column mappings
    """
    kind: str
    table: str
    id_column: str
    id_length: int
    fields: Tuple[_SeriesField, ...]


_TIMESERIES_TOPICS: Tuple[_TimeseriesTopic, ...] = (
    _TimeseriesTopic(
        kind=OBJECTS.NODE,
        table='rpt_node',
        id_column='node_id',
        id_length=16,
        fields=(
            _SeriesField('flooding', ('flooding',)),
            _SeriesField('depth', ('depth',)),
            _SeriesField('head', ('head',)),
            _SeriesField('inflow', ('total_inflow',)),
        ),
    ),
    _TimeseriesTopic(
        kind=OBJECTS.LINK,
        table='rpt_arc',
        id_column='arc_id',
        id_length=16,
        fields=(
            _SeriesField('flow', ('flow',)),
            _SeriesField('velocity', ('velocity',)),
            # SWMM stores capacity as the fraction of the full area filled by flow;
            # the report's "Percent Full" column is that fraction scaled to percent.
            _SeriesField('fullpercent', ('capacity',), 100.0),
        ),
    ),
    _TimeseriesTopic(
        kind=OBJECTS.SUBCATCHMENT,
        table='rpt_subcatchment',
        id_column='subc_id',
        id_length=16,
        fields=(
            _SeriesField('precip', ('rainfall',)),
            # SWMM reports subcatchment losses as evaporation plus infiltration.
            _SeriesField('losses', ('evaporation', 'infiltration')),
            _SeriesField('runoff', ('runoff',)),
        ),
    ),
)

_MONTH_ABBREVIATIONS = (
    'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN',
    'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC',
)


def _rollback(dao: HePgDao, owns_transaction: bool) -> None:
    """Roll back the transaction when this export opened it."""
    if not owns_transaction:
        return
    try:
        dao.rollback()
    except DatabaseError:
        pass


def _format_timestamps(index: Sequence[Any]) -> Tuple[List[str], List[str]]:
    """
    Split the OUT datetime index into Giswater's date and time strings.

    The report-style ``MON-DD-YYYY`` form is built from a fixed month table so the
    values do not depend on the machine locale.

    :param index: Datetime index of the results
    :return: Tuple of (date strings, time strings)
    """
    dates: List[str] = []
    times: List[str] = []
    for stamp in index:
        dates.append(f"{_MONTH_ABBREVIATIONS[stamp.month - 1]}-{stamp.day:02d}-{stamp.year}")
        times.append(f"{stamp.hour:02d}:{stamp.minute:02d}:{stamp.second:02d}")
    return dates, times


def _variable_matrix(
    results: SwmmOutput,
    kind: str,
    labels: Sequence[str],
    variable: str,
) -> Optional[np.ndarray]:
    """
    Read one OUT variable for every element of a kind as a time x element matrix.

    Only the variables Giswater stores are requested. swmm_api caches the decoded
    binary on the first read, so the file is still touched once, while asking for
    one variable at a time keeps just the exported columns in memory. It then
    collapses the column index to the element labels, or to a Series when the
    model holds a single element.

    :param results: Loaded SwmmOutput object
    :param kind: OUT object kind
    :param labels: Element labels, defining the column order
    :param variable: OUT variable name
    :return: Float matrix with shape (time steps, elements), or None if unavailable
    """
    part = results.get_part(kind=kind, variable=variable, show_progress=False)
    if part is None:
        return None

    if isinstance(part, pd.Series):
        if len(labels) != 1:
            return None
        return part.to_numpy(dtype=np.float64).reshape(-1, 1)

    if part.empty:
        return None

    columns = part.columns
    if isinstance(columns, pd.MultiIndex):
        for level in range(columns.nlevels):
            if set(labels).issubset(set(columns.get_level_values(level))):
                part = part.copy()
                part.columns = columns.get_level_values(level)
                break
        else:
            return None

    return part.reindex(columns=list(labels)).to_numpy(dtype=np.float64)


def _field_matrix(
    results: SwmmOutput,
    topic: _TimeseriesTopic,
    labels: Sequence[str],
    field: _SeriesField,
    available: Set[str],
    round_decimals: int,
) -> Optional[np.ndarray]:
    """
    Build the rounded matrix backing one Giswater column.

    :param results: Loaded SwmmOutput object
    :param topic: Mapping definition for this object kind
    :param labels: Element labels, defining the column order
    :param field: Column mapping
    :param available: Variables present in the OUT file for this kind
    :param round_decimals: Decimal places to round to
    :return: Float matrix or None when no source variable is available
    """
    total: Optional[np.ndarray] = None
    for variable in field.variables:
        if variable not in available:
            continue
        matrix = _variable_matrix(results, topic.kind, labels, variable)
        if matrix is None:
            continue
        total = matrix if total is None else total + matrix

    if total is None:
        return None
    if field.scale != 1.0:
        total = total * field.scale
    return np.round(total, round_decimals)


def _iter_timeseries_records(
    result_id: str,
    element_ids: Sequence[Optional[str]],
    dates: Sequence[str],
    times: Sequence[str],
    matrices: Sequence[np.ndarray],
) -> Iterator[Tuple[Any, ...]]:
    """
    Yield time-series rows for PostgreSQL COPY streaming.

    Rows are produced one time step at a time and each step's values are converted
    to Python floats in bulk, so only a single step is materialized at a time.

    :param result_id: Result identifier
    :param element_ids: Element identifiers in matrix column order
    :param dates: Date string per time step
    :param times: Time string per time step
    :param matrices: One matrix per exported column
    :return: Row iterator
    """
    for time_index, date in enumerate(dates):
        time = times[time_index]
        # NaN marks a step SWMM did not report for the element; tolist() also
        # converts the whole step to Python floats in one pass.
        step_values = [
            [None if value != value else value for value in matrix[time_index].tolist()]
            for matrix in matrices
        ]
        for element_index, element_id in enumerate(element_ids):
            yield (result_id, element_id, date, time) + tuple(
                values[element_index] for values in step_values
            )


def _export_timeseries(
    dao: HePgDao,
    results: SwmmOutput,
    result_id: str,
    topic: _TimeseriesTopic,
    round_decimals: int,
    allowed_columns: Set[str],
    selection: ReportKindSelection,
) -> int:
    """
    Copy the time series of one object kind into its Giswater table.

    :param dao: Database access object
    :param results: Loaded SwmmOutput object
    :param result_id: Result identifier
    :param topic: Mapping definition for this object kind
    :param round_decimals: Decimal places to round to
    :param allowed_columns: Columns present in the target table
    :param selection: REPORT selection for this kind (ALL or ID set)
    :return: Number of rows inserted
    """
    labels = filter_labels_by_selection(
        list(results.labels.get(topic.kind) or []),
        selection,
    )
    if not labels:
        return 0

    available = set(results.variables.get(topic.kind) or [])
    columns: List[str] = []
    matrices: List[np.ndarray] = []
    for field in topic.fields:
        if field.column not in allowed_columns:
            continue
        matrix = _field_matrix(results, topic, labels, field, available, round_decimals)
        if matrix is None:
            continue
        columns.append(field.column)
        matrices.append(matrix)

    if not matrices:
        tools_log.log_warning(f"No {topic.kind} results available in OUT file, skipping {topic.table}")
        return 0

    dates, times = _format_timestamps(results.index)
    element_ids = [truncate_text(label, topic.id_length) for label in labels]

    records = _iter_timeseries_records(result_id, element_ids, dates, times, matrices)
    copy_columns = [topic.id_column, 'resultdate', 'resulttime'] + columns
    count = copy_records(dao, topic.table, ['result_id'] + copy_columns, records)
    tools_log.log_info(f"Inserted {count} rows into {topic.table}")
    return count

# endregion

# region Helper functions

def _prepare_nodes_data(inp_data: SwmmInput) -> List[Dict]:
    """Extract node data from SWMM input file."""
    nodes_data = []
    for node_id, coordinates in inp_data['COORDINATES'].items():
        node_type = tools_sensorthings.get_swmm_node_type(node_id, inp_data)

        nodes_data.append({
            'id': node_id,
            'type': node_type,
            'coordinates': (coordinates.x, coordinates.y)
        })

    return nodes_data


def _prepare_nodes_things_data(
    nodes_data: List[Dict], results: SwmmOutput, sensor_ids: Dict[str, str],
    property_ids: Dict[str, str], transformer: Transformer,
    inp_feature_ids: set
) -> List[Dict]:
    """Prepare Thing data for nodes (no HTTP calls)."""
    things_data = []
    export_errors: List[str] = []
    for node_data in nodes_data:
        node_id = node_data['id']
        node_type = node_data['type']
        coordinates = node_data['coordinates']

        # Track this feature ID
        inp_feature_ids.add(node_id)

        # Transform coordinates
        lon, lat = transformer.transform(coordinates[0], coordinates[1])
        location = {"type": "Point", "coordinates": [lon, lat]}

        # Create Datastreams with Observations for each property
        datastreams = []
        for prop in tools_sensorthings.SWMM_NODE_PROPERTIES:
            prop_config = tools_sensorthings.SWMM_OBSERVED_PROPERTIES[prop]
            try:
                values = results.get_part('node', node_id, prop)

                observations = []
                current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

                for timestamp, value in values.items():
                    observations.append({
                        "phenomenonTime": timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        "result": float(value),
                        "resultTime": current_time
                    })

                datastream = {
                    "name": f"{prop_config['name']} at {node_id}",
                    "description": f"The {prop_config['name'].lower()} at SWMM {node_type} {node_id}",
                    "unitOfMeasurement": prop_config['unit'],
                    "observationType": "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement",
                    "Sensor": {"@iot.id": sensor_ids['simulated']},
                    "ObservedProperty": {"@iot.id": property_ids[prop]},
                    "Observations": observations
                }
                datastreams.append(datastream)

            except Exception as e:
                msg = f"Could not process {prop} for {node_id}: {e}"
                tools_log.log_warning(msg)
                export_errors.append(msg)

        thing_data = {
            "name": node_id,
            "description": f"SWMM {node_type} {node_id}",
            "Locations": [{
                "name": f"{node_id} Location",
                "description": f"Location of SWMM {node_type} {node_id}",
                "encodingType": "application/geo+json",
                "location": location
            }],
            "Datastreams": datastreams,
            "properties": {
                "node_type": node_type
            }
        }
        things_data.append(thing_data)

    if export_errors:
        raise ExportError(
            "FROST export failed while preparing node Things: " + "; ".join(export_errors)
        )

    return things_data


def _prepare_links_data(inp_data: SwmmInput) -> List[Dict]:
    """Extract link data from SWMM input file."""
    links_data = []

    # Process all link types
    link_types = ['CONDUITS', 'PUMPS', 'ORIFICES', 'WEIRS', 'OUTLETS']
    for link_section in link_types:
        if link_section in inp_data:
            for link_id in inp_data[link_section]:
                link_type = tools_sensorthings.get_swmm_link_type(link_id, inp_data)

                links_data.append({
                    'id': link_id,
                    'type': link_type
                })

    return links_data


def _prepare_links_things_data(
    links_data: List[Dict], results, sensor_ids: Dict[str, str],
    property_ids: Dict[str, str], inp_data: SwmmInput, transformer: Transformer,
    inp_feature_ids: set
) -> List[Dict]:
    """Prepare Thing data for links (no HTTP calls)."""
    things_data = []
    export_errors: List[str] = []
    for link_data in links_data:
        link_id = link_data['id']
        link_type = link_data['type']

        # Track this feature ID
        inp_feature_ids.add(link_id)

        link_info = inp_data[f'{link_type}S'][link_id]
        vertices = _get_geometry_from_link(inp_data, link_info)

        transformed_vertices = []
        for x, y in vertices:
            lon, lat = transformer.transform(x, y)
            transformed_vertices.append([lon, lat])

        datastreams = []
        for prop in tools_sensorthings.SWMM_LINK_PROPERTIES:
            prop_config = tools_sensorthings.SWMM_OBSERVED_PROPERTIES[prop]
            try:
                values = results.get_part('link', link_id, prop)

                observations = []
                current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

                for timestamp, value in values.items():
                    observations.append({
                        "phenomenonTime": timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'),
                        "result": float(value),
                        "resultTime": current_time
                    })

                datastream = {
                    "name": f"{prop_config['name']} at {link_id}",
                    "description": f"The {prop_config['name'].lower()} at SWMM {link_type} {link_id}",
                    "unitOfMeasurement": prop_config['unit'],
                    "observationType": "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement",
                    "Sensor": {"@iot.id": sensor_ids['simulated']},
                    "ObservedProperty": {"@iot.id": property_ids[prop]},
                    "Observations": observations
                }
                datastreams.append(datastream)

            except Exception as e:
                msg = f"Could not process {prop} for {link_id}: {e}"
                tools_log.log_warning(msg)
                export_errors.append(msg)

        thing_data = {
            "name": link_id,
            "description": f"SWMM {link_type} {link_id}",
            "Locations": [{
                "name": f"{link_id} Location",
                "description": f"Location of SWMM {link_type} {link_id}",
                "encodingType": "application/geo+json",
                "location": {
                    "type": "LineString",
                    "coordinates": transformed_vertices
                }
            }],
            "Datastreams": datastreams,
            "properties": {
                "link_type": link_type
            }
        }
        things_data.append(thing_data)

    if export_errors:
        raise ExportError(
            "FROST export failed while preparing link Things: " + "; ".join(export_errors)
        )

    return things_data


def _get_geometry_from_link(inp, link) -> list[tuple[float, float]]:
    """Get geometry coordinates for a link including vertices."""
    from_node = link.from_node
    if from_node not in inp[COORDINATES]:
        raise ValidationError(
            f"Link {link.name} has invalid geometry: missing coordinates on node {from_node}"
        )
    to_node = link.to_node
    if to_node not in inp[COORDINATES]:
        raise ValidationError(
            f"Link {link.name} has invalid geometry: missing coordinates on node {to_node}"
        )

    start_node_x, start_node_y = inp[COORDINATES][from_node].x, inp[COORDINATES][from_node].y
    end_node_x, end_node_y = inp[COORDINATES][to_node].x, inp[COORDINATES][to_node].y
    vertices = inp[VERTICES][link.name].vertices if link.name in inp[VERTICES] else []

    coordinates = []
    coordinates.append((start_node_x, start_node_y))
    for v in vertices:
        coordinates.append((v[0], v[1]))
    coordinates.append((end_node_x, end_node_y))

    return coordinates

# endregion
