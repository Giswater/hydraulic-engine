"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
import wntr

from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from pyproj import Transformer
from datetime import timedelta
from wntr.epanet.util import from_si

from .file_handler import EpanetResultHandler, EpanetFileHandler
from .inp_handler import EpanetInpHandler
from ..utils import tools_log
from ..utils.tools_api import get_api_client, HeFrostClient
from ..utils import tools_sensorthings
from ..exceptions import (
    ModelNotLoadedError,
    DatabaseError,
    ExportError,
    SimulationError,
    APIError,
)
from ..utils.tools_db import HePgDao, get_connection


class EpanetBinHandler(EpanetFileHandler, EpanetResultHandler):
    """
    Handler for EPANET BIN (binary) files.
    
    Provides functionality to read and parse EPANET simulation output.

    Note: This module uses private helper functions (_prepare_*) 
    for data preparation tasks. These are not part of the public API.
    
    Example usage:
        handler = EpanetBinHandler()
        handler.load_file("results.bin")
        handler.export_to_frost(inp_handler=inp_handler, result_id="test1")
        handler.export_to_database(result_id="test1")
    """

    def export_to_database(
            self,
            result_id: str,
            inp_handler: EpanetInpHandler,
            round_decimals: int = 2,
            dao: Optional[HePgDao] = None,
            giswater_version: int = 4,
            only_extrema: bool = False
        ) -> bool:
        """
        Export simulation results to Giswater database.
        
        Fills the following tables:
        - rpt_node: Time series node results (demand, head, pressure, quality)
        - rpt_arc: Time series arc results (flow, velocity, headloss, etc.)
        - rpt_node_stats: Aggregated node statistics (max/min/avg)
        - rpt_arc_stats: Aggregated arc statistics (max/min/avg)
        - selector_rpt_main: Sets the current result for visualization
        - rpt_cat_result: Updates execution metadata
        
        Prerequisites:
        - The rpt_inp_node and rpt_inp_arc tables must be populated by the plugin
          (via gw_fct_pg2epa_main) before calling this method.
        
        :param result_id: The result identifier (must match rpt_cat_result.result_id)
        :param inp_handler: INP handler to get coordinates
        :param round_decimals: Number of decimal places to round the results (default: 2)
        :param dao: Database access object (optional, uses global connection if not provided)
        :param giswater_version: Version of Giswater (default: 4)
        :param only_extrema: If True, skip time series inserts and only export aggregated stats
        :return: True if export successful, False otherwise
        """
        if not self.is_loaded():
            raise ModelNotLoadedError("No binary file loaded")

        if dao is None:
            dao = get_connection()

        if dao is None or not dao.is_connected():
            raise DatabaseError("No database connection available")

        results: wntr.sim.SimulationResults = self.file_object

        try:
            tools_log.log_info(f"Starting export to database for result_id: {result_id}")

            tools_log.log_info("Cleaning previous results...")
            _clean_previous_results(dao, result_id, giswater_version)

            tools_log.log_info("Building node and arc data...")
            node_data = _build_node_data(results, inp_handler, round_decimals)
            arc_data = _build_arc_data(results, inp_handler, round_decimals)

            if not only_extrema:
                tools_log.log_info("Inserting node results...")
                node_count = _insert_node_results(dao, node_data, result_id, giswater_version)
                tools_log.log_info(f"Inserted {node_count} node result records")

                tools_log.log_info("Inserting arc results...")
                arc_count = _insert_arc_results(dao, arc_data, result_id)
                tools_log.log_info(f"Inserted {arc_count} arc result records")

                tools_log.log_info("Post-processing arc results...")
                _post_process_arcs(dao, result_id)
            else:
                tools_log.log_info("Skipping time series inserts (only_extrema=True)")

            if giswater_version > 3:
                tools_log.log_info("Calculating node statistics...")
                _insert_node_stats(dao, result_id, node_data, round_decimals, giswater_version)

                tools_log.log_info("Calculating arc statistics...")
                _insert_arc_stats(dao, result_id, arc_data, round_decimals)

            tools_log.log_info("Updating result catalog and selectors...")
            _finalize_import(dao, result_id, giswater_version)

            dao.commit()
            tools_log.log_info(f"Export to database completed successfully for result_id: {result_id}")
            return True

        except (DatabaseError, ExportError, SimulationError, ModelNotLoadedError):
            try:
                dao.rollback()
            except DatabaseError:
                pass
            raise
        except Exception as e:
            tools_log.log_error(f"Error exporting to database: {e}")
            try:
                dao.rollback()
            except DatabaseError:
                pass
            raise ExportError(f"Error exporting to database: {e}") from e

    def export_to_frost(
            self,
            inp_handler: EpanetFileHandler,
            result_id: str,
            batch_size: int = 50,
            max_workers: int = 4,
            crs_from: int = 25831,
            crs_to: int = 4326,
            start_time: Optional[datetime] = None,
            client: Optional[HeFrostClient] = None
        ) -> bool:
        """
        Export simulation results to FROST-Server (SensorThings API).
        
        Creates Things for nodes and links, Datastreams for each output variable, and Observations for the time series data.
        
        :param inp_handler: INP handler to get coordinates
        :param result_id: ID of the result
        :param batch_size: Number of operations per batch request (default: 200)
        :param crs_from: Source CRS code (default: 25831 - ETRS89 / UTM zone 31N)
        :param crs_to: Target CRS code (default: 4326 - WGS84)
        :param network_type: Type of network (default: "EPANET")
        :param start_time: Simulation start time (default: None, uses current time + start_clocktime)
        :param max_workers: Number of concurrent batch requests (default: 4)
        """
        if client is None:
            client = get_api_client()

        if not client or not isinstance(client, HeFrostClient):
            raise APIError("No FROST client available")

        if not self.is_loaded():
            raise ModelNotLoadedError("No binary file loaded")

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

        # Determine simulation start time
        if start_time is None:
            start_time = datetime.now(timezone.utc) + timedelta(seconds=inp_handler.file_object.options.time.start_clocktime)
        tools_log.log_info(f"Simulation start time: {start_time.isoformat()}")

        # Pre-fetch existing entities (optimized: 2 API calls instead of N)
        tools_log.log_info("Fetching existing entities from server...")
        things_cache = tools_sensorthings.get_all_things_with_locations(client)
        obs_props_cache = tools_sensorthings.get_all_observed_properties(client)
        tools_log.log_info(f"Found {len(things_cache)} existing Things and {len(obs_props_cache)} ObservedProperties")

        # Get or create ObservedProperties (only creates missing ones)
        property_ids = tools_sensorthings.get_or_create_observed_properties(
            obs_props_cache=obs_props_cache,
            engine='epanet',
            client=client
        )

        # Create new Sensor for this simulation run
        sensor_ids = tools_sensorthings.create_simulation_sensor(
            result_id=result_id,
            network_type='EPANET',
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
            nodes_data, inp_handler.file_object, self.file_object, sensor_ids, property_ids,
            transformer, start_time, inp_feature_ids
        )

        tools_log.log_info("Preparing links...")
        links_data = _prepare_links_data(inp_handler.file_object)
        tools_log.log_info(f"Found {len(links_data)} links")

        link_things = _prepare_links_things_data(
            links_data, self.file_object, sensor_ids, property_ids,
            inp_handler.file_object, transformer, start_time, inp_feature_ids
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


# region Export to Database Helper Functions

def _seconds_to_time_str(seconds: int) -> str:
    """
    Convert seconds to HH:MM:SS time string format.
    
    :param seconds: Time in seconds
    :return: Time string in HH:MM:SS format
    """
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h}:{m:02d}:{s:02d}"


def _clean_previous_results(dao: HePgDao, result_id: str, giswater_version: int = 4) -> None:
    """
    Clean previous results for the given result_id from all rpt tables.
    
    :param dao: Database access object
    :param result_id: Result identifier
    :raises DatabaseError: If a delete statement fails
    """
    tables_to_clean = [
        'rpt_node',
        'rpt_arc',
        'rpt_energy_usage',
        'rpt_hydraulic_status'
    ]
    if giswater_version > 3:
        tables_to_clean.append('rpt_node_stats')
        tables_to_clean.append('rpt_arc_stats')

    for table in tables_to_clean:
        sql = f"DELETE FROM {table} WHERE result_id = %s"
        try:
            dao.execute(sql, (result_id,), commit=False)
        except DatabaseError as e:
            raise DatabaseError(f"Failed to clean {table}") from e


def _build_node_data(
    results: wntr.sim.SimulationResults,
    inp_handler: EpanetInpHandler,
    round_decimals: int = 2
) -> List[Dict[str, Any]]:
    """
    Build converted node time-series data once for reuse in inserts and stats.
    """
    unit_system = getattr(wntr.epanet.util.FlowUnits, inp_handler.file_object.options.hydraulic.inpfile_units)
    if unit_system is None:
        tools_log.log_error(f"Invalid unit system: {inp_handler.file_object.options.hydraulic.inpfile_units}")
        raise SimulationError(
            f"Invalid unit system: {inp_handler.file_object.options.hydraulic.inpfile_units}"
        )

    node_data = results.node
    if node_data is None:
        raise SimulationError("No node data found in results")

    if 'demand' not in node_data:
        raise SimulationError("No demand data found in results")

    demand_df = node_data['demand']
    node_ids = demand_df.columns.tolist()
    time_steps = demand_df.index.tolist()
    if time_steps is None or len(time_steps) == 0:
        raise SimulationError("No time steps found in results")

    records: List[Dict[str, Any]] = []
    for time_sec in time_steps:
        time_str = _seconds_to_time_str(int(time_sec))
        for node_id in node_ids:
            top_elev = _convert_from_si(
                value=inp_handler.file_object.nodes[node_id].elevation,
                unit_system=unit_system,
                param=wntr.epanet.util.HydParam.Elevation,
                round_decimals=round_decimals
            ) if getattr(inp_handler.file_object.nodes[node_id], 'elevation', None) is not None else None
            demand = _convert_from_si(
                value=demand_df.loc[time_sec, node_id],
                unit_system=unit_system,
                param=wntr.epanet.util.HydParam.Demand,
                round_decimals=round_decimals
            ) if 'demand' in node_data else None
            head = _convert_from_si(
                value=node_data['head'].loc[time_sec, node_id],
                unit_system=unit_system,
                param=wntr.epanet.util.HydParam.HydraulicHead,
                round_decimals=round_decimals
            ) if 'head' in node_data else None
            pressure = _convert_from_si(
                value=node_data['pressure'].loc[time_sec, node_id],
                unit_system=unit_system,
                param=wntr.epanet.util.HydParam.Pressure,
                round_decimals=round_decimals
            ) if 'pressure' in node_data else None
            quality = round(float(node_data['quality'].loc[time_sec, node_id]), round_decimals) if 'quality' in node_data else None

            records.append({
                'node_id': node_id,
                'time': time_str,
                'top_elev': top_elev,
                'demand': demand,
                'head': head,
                'press': pressure,
                'quality': quality
            })

    return records


def _insert_node_results(
    dao: HePgDao,
    node_data: List[Dict[str, Any]],
    result_id: str,
    giswater_version: int = 4
) -> int:
    """
    Insert time series node results into rpt_node table.
    
    :param dao: Database access object
    :param node_data: List of node data
    :param result_id: Result identifier
    :param giswater_version: Version of Giswater (default: 4)
    :return: Number of records inserted
    """
    records = [
        (result_id, row['node_id'], row['time'], row['top_elev'], row['demand'], row['head'], row['press'], row['quality'])
        for row in node_data
    ]

    elevation_column = 'elevation' if giswater_version == 3 else 'top_elev'

    sql = f"""
        INSERT INTO rpt_node (result_id, node_id, time, {elevation_column}, demand, head, press, quality)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    count = 0
    if dao.cursor:
        dao.cursor.executemany(sql, records)
        count = len(records)

    return count


def _build_arc_data(
    results: wntr.sim.SimulationResults,
    inp_handler: EpanetInpHandler,
    round_decimals: int = 2
) -> List[Dict[str, Any]]:
    """
    Build converted arc time-series data once for reuse in inserts and stats.
    """
    unit_system = getattr(wntr.epanet.util.FlowUnits, inp_handler.file_object.options.hydraulic.inpfile_units)
    if unit_system is None:
        tools_log.log_error(f"Invalid unit system: {inp_handler.file_object.options.hydraulic.inpfile_units}")
        raise SimulationError(
            f"Invalid unit system: {inp_handler.file_object.options.hydraulic.inpfile_units}"
        )

    link_data = results.link
    if link_data is None:
        raise SimulationError("No link data found in results")

    if 'flowrate' not in link_data:
        tools_log.log_warning("No flowrate data found in results")
        raise SimulationError("No flowrate data found in results")

    flow_df = link_data['flowrate']
    link_ids = flow_df.columns.tolist()
    time_steps = flow_df.index.tolist()
    if time_steps is None or len(time_steps) == 0:
        raise SimulationError("No time steps found in results")

    records: List[Dict[str, Any]] = []
    for time_sec in time_steps:
        time_str = _seconds_to_time_str(int(time_sec))
        for link_id in link_ids:
            length = _convert_from_si(
                value=inp_handler.file_object.links[link_id].length,
                unit_system=unit_system,
                param=wntr.epanet.util.HydParam.Length,
                round_decimals=round_decimals
            ) if getattr(inp_handler.file_object.links[link_id], 'length', None) is not None else None
            diameter = _convert_from_si(
                value=inp_handler.file_object.links[link_id].diameter,
                unit_system=unit_system,
                param=wntr.epanet.util.HydParam.PipeDiameter,
                round_decimals=round_decimals
            ) if getattr(inp_handler.file_object.links[link_id], 'diameter', None) is not None else None
            flow = _convert_from_si(
                value=flow_df.loc[time_sec, link_id],
                unit_system=unit_system,
                param=wntr.epanet.util.HydParam.Flow,
                round_decimals=round_decimals
            ) if 'flowrate' in link_data else None
            velocity = _convert_from_si(
                value=link_data['velocity'].loc[time_sec, link_id],
                unit_system=unit_system,
                param=wntr.epanet.util.HydParam.Velocity,
                round_decimals=round_decimals
            ) if 'velocity' in link_data else None
            headloss = _convert_from_si(
                value=link_data['headloss'].loc[time_sec, link_id],
                unit_system=unit_system,
                param=wntr.epanet.util.HydParam.HeadLoss,
                round_decimals=round_decimals
            ) if 'headloss' in link_data else None
            setting = round(float(link_data['setting'].loc[time_sec, link_id]), round_decimals) if 'setting' in link_data else None
            reaction = round(float(link_data['reaction_rate'].loc[time_sec, link_id]), round_decimals) if 'reaction_rate' in link_data else None
            ffactor = round(float(link_data['friction_factor'].loc[time_sec, link_id]), round_decimals) if 'friction_factor' in link_data else None

            status = None
            if 'status' in link_data:
                status_val = int(link_data['status'].loc[time_sec, link_id])
                status_map = {0: 'CLOSED', 1: 'OPEN', 2: 'ACTIVE'}
                status = status_map.get(status_val, str(status_val))

            records.append({
                'arc_id': link_id,
                'time': time_str,
                'length': length,
                'diameter': diameter,
                'flow': flow,
                'vel': velocity,
                'headloss': headloss,
                'setting': setting,
                'reaction': reaction,
                'ffactor': ffactor,
                'status': status
            })

    return records


def _insert_arc_results(dao: HePgDao, arc_data: List[Dict[str, Any]], result_id: str) -> int:
    """
    Insert time series arc results into rpt_arc table.
    
    :param dao: Database access object
    :param arc_data: List of arc data
    :param result_id: Result identifier
    :return: Number of records inserted
    """
    records = [
        (
            result_id,
            row['arc_id'],
            row['time'],
            row['length'],
            row['diameter'],
            row['flow'],
            row['vel'],
            row['headloss'],
            row['setting'],
            row['reaction'],
            row['ffactor'],
            row['status']
        )
        for row in arc_data
    ]

    sql = """
        INSERT INTO rpt_arc (result_id, arc_id, time, length, diameter, flow, vel, headloss, setting, reaction, ffactor, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    count = 0
    if dao.cursor:
        dao.cursor.executemany(sql, records)
        count = len(records)

    return count


def _post_process_arcs(dao: HePgDao, result_id: str) -> None:
    """
    Post-process arc results:
    - Reverse geometry in rpt_inp_arc where flow is negative
    - Update flow values to absolute value in rpt_arc
    
    :param dao: Database access object
    :param result_id: Result identifier
    """
    # Reverse geometries where flow is negative
    sql_reverse = """
        UPDATE rpt_inp_arc 
        SET the_geom = ST_Reverse(the_geom) 
        FROM rpt_arc 
        WHERE rpt_arc.arc_id = rpt_inp_arc.arc_id
        AND rpt_arc.result_id = rpt_inp_arc.result_id
        AND rpt_arc.flow < 0 
        AND rpt_inp_arc.result_id = %s
    """
    dao.execute(sql_reverse, (result_id,), commit=False)

    # Update flow to absolute value
    sql_abs_flow = """
        UPDATE rpt_arc 
        SET flow = ABS(flow) 
        WHERE flow < 0 AND result_id = %s
    """
    dao.execute(sql_abs_flow, (result_id,), commit=False)


def _metric_stats(
    values: List[Tuple[float, str]],
    round_decimals: int
) -> tuple[Optional[float], Optional[str], Optional[float], Optional[str], Optional[float]]:
    """Return max, t_max, min, t_min and avg for a metric series."""
    if not values:
        return None, None, None, None, None
    max_value, max_time = max(values, key=lambda item: item[0])
    min_value, min_time = min(values, key=lambda item: item[0])
    avg_value = round(sum(value for value, _ in values) / len(values), round_decimals)
    return max_value, max_time, min_value, min_time, avg_value


def _insert_node_stats(
    dao: HePgDao,
    result_id: str,
    node_data: List[Dict[str, Any]],
    round_decimals: int = 2,
    giswater_version: int = 4
) -> None:
    """
    Calculate and insert node statistics into rpt_node_stats table.
    
    Statistics are calculated from in-memory node time-series data and joined
    with rpt_inp_node for metadata and geometry.
    
    :param dao: Database access object
    :param result_id: Result identifier
    :param node_data: Converted node time-series records
    :param round_decimals: Number of decimal places for averages
    :param giswater_version: Version of Giswater (default: 4)
    """
    grouped: Dict[str, Dict[str, List[Tuple[float, str]]]] = {}

    for row in node_data:
        node_id = row['node_id']
        if node_id not in grouped:
            grouped[node_id] = {'demand': [], 'head': [], 'press': [], 'quality': []}

        for metric in ('demand', 'head', 'press', 'quality'):
            value = row[metric]
            if value is not None:
                grouped[node_id][metric].append((value, row['time']))

    elevation_column = 'elevation' if giswater_version == 3 else 'top_elev'

    sql = f"""
        INSERT INTO rpt_node_stats (
            node_id, result_id, node_type, sector_id, nodecat_id, {elevation_column},
            demand_max, demand_min, demand_avg, t_demand_max, t_demand_min,
            head_max, head_min, head_avg, t_head_max, t_head_min,
            press_max, press_min, press_avg, t_press_max, t_press_min,
            quality_max, quality_min, quality_avg, t_quality_max, t_quality_min,
            the_geom
        )
        SELECT
            node.node_id, %s, node.node_type, node.sector_id, node.nodecat_id, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            node.the_geom
        FROM rpt_inp_node node
        WHERE node.result_id = %s AND node.node_id::text = %s
    """

    records = []
    for node_id, values in grouped.items():
        demand_max, demand_max_time, demand_min, demand_min_time, demand_avg = _metric_stats(values['demand'], round_decimals)
        head_max, head_max_time, head_min, head_min_time, head_avg = _metric_stats(values['head'], round_decimals)
        press_max, press_max_time, press_min, press_min_time, press_avg = _metric_stats(values['press'], round_decimals)
        quality_max, quality_max_time, quality_min, quality_min_time, quality_avg = _metric_stats(values['quality'], round_decimals)
        elevation = head_max

        records.append((
            result_id, elevation,
            demand_max, demand_min, demand_avg, demand_max_time, demand_min_time,
            head_max, head_min, head_avg, head_max_time, head_min_time,
            press_max, press_min, press_avg, press_max_time, press_min_time,
            quality_max, quality_min, quality_avg, quality_max_time, quality_min_time,
            result_id, node_id
        ))

    if dao.cursor and records:
        dao.cursor.executemany(sql, records)
        if dao.cursor.rowcount == 0:
            raise ExportError("No rows inserted into rpt_node_stats")


def _insert_arc_stats(
    dao: HePgDao,
    result_id: str,
    arc_data: List[Dict[str, Any]],
    round_decimals: int = 2
) -> None:
    """
    Calculate and insert arc statistics into rpt_arc_stats table.
    
    Statistics are calculated from in-memory arc time-series data and joined
    with rpt_inp_arc for metadata and geometry.
    
    :param dao: Database access object
    :param result_id: Result identifier
    :param arc_data: Converted arc time-series records
    :param round_decimals: Number of decimal places for averages
    """
    grouped: Dict[str, Dict[str, List[Tuple[float, str]]]] = {}
    length_map: Dict[str, Optional[float]] = {}

    for row in arc_data:
        arc_id = row['arc_id']
        if arc_id not in grouped:
            grouped[arc_id] = {'flow': [], 'vel': [], 'headloss': [], 'setting': [], 'reaction': [], 'ffactor': []}
            length_map[arc_id] = row['length']

        for metric in ('flow', 'vel', 'headloss', 'setting', 'reaction', 'ffactor'):
            value = row[metric]
            if value is not None:
                time_value = row['time']
                if metric == 'flow':
                    grouped[arc_id][metric].append((abs(value), time_value))
                else:
                    grouped[arc_id][metric].append((value, time_value))

    sql = """
        INSERT INTO rpt_arc_stats (
            arc_id, result_id, arc_type, sector_id, arccat_id,
            flow_max, flow_min, flow_avg, t_flow_max, t_flow_min,
            vel_max, vel_min, vel_avg, t_vel_max, t_vel_min,
            headloss_max, headloss_min, t_headloss_max, t_headloss_min,
            setting_max, setting_min, t_setting_max, t_setting_min,
            reaction_max, reaction_min, t_reaction_max, t_reaction_min,
            ffactor_max, ffactor_min, t_ffactor_max, t_ffactor_min,
            length, tot_headloss_max, tot_headloss_min,
            the_geom
        )
        SELECT
            arc.arc_id, %s, arc.arc_type, arc.sector_id, arc.arccat_id,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            arc.the_geom
        FROM rpt_inp_arc arc
        WHERE arc.result_id = %s AND arc.arc_id::text = %s
    """

    records = []
    for arc_id, values in grouped.items():
        flow_max, flow_max_time, flow_min, flow_min_time, flow_avg = _metric_stats(values['flow'], round_decimals)
        vel_max, vel_max_time, vel_min, vel_min_time, vel_avg = _metric_stats(values['vel'], round_decimals)
        headloss_max, headloss_max_time, headloss_min, headloss_min_time, _ = _metric_stats(values['headloss'], round_decimals)
        setting_max, setting_max_time, setting_min, setting_min_time, _ = _metric_stats(values['setting'], round_decimals)
        reaction_max, reaction_max_time, reaction_min, reaction_min_time, _ = _metric_stats(values['reaction'], round_decimals)
        ffactor_max, ffactor_max_time, ffactor_min, ffactor_min_time, _ = _metric_stats(values['ffactor'], round_decimals)
        length = length_map[arc_id]

        tot_headloss_max = None if headloss_max is None or length is None else round(headloss_max * length / 1000, round_decimals)
        tot_headloss_min = None if headloss_min is None or length is None else round(headloss_min * length / 1000, round_decimals)

        records.append((
            result_id,
            flow_max, flow_min, flow_avg, flow_max_time, flow_min_time,
            vel_max, vel_min, vel_avg, vel_max_time, vel_min_time,
            headloss_max, headloss_min, headloss_max_time, headloss_min_time,
            setting_max, setting_min, setting_max_time, setting_min_time,
            reaction_max, reaction_min, reaction_max_time, reaction_min_time,
            ffactor_max, ffactor_min, ffactor_max_time, ffactor_min_time,
            length, tot_headloss_max, tot_headloss_min,
            result_id, arc_id
        ))

    if dao.cursor and records:
        dao.cursor.executemany(sql, records)
        if dao.cursor.rowcount == 0:
            raise ExportError("No rows inserted into rpt_arc_stats")


def _finalize_import(dao: HePgDao, result_id: str, giswater_version: int = 4) -> None:
    """
    Finalize the import process:
    - Update rpt_cat_result with execution metadata
    - Set selector_rpt_main for current user
    - Clean up null time values
    
    :param dao: Database access object
    :param result_id: Result identifier
    """
    # Update rpt_cat_result
    if giswater_version == 3:
        sql_update_result = """
            UPDATE rpt_cat_result 
            SET exec_date = now(), cur_user = current_user, status = 2, 
            expl_id = (SELECT array_agg(expl_id) FROM selector_expl WHERE cur_user = current_user AND expl_id > 0)[1]
            WHERE result_id = %s
        """
    else:
        sql_update_result = """
            UPDATE rpt_cat_result 
            SET exec_date = now(), cur_user = current_user, status = 2, 
            expl_id = (SELECT array_agg(expl_id) FROM selector_expl WHERE cur_user = current_user AND expl_id > 0),
            sector_id = (SELECT array_agg(sector_id) FROM selector_sector WHERE cur_user = current_user AND sector_id > 0)
            WHERE result_id = %s
        """

    dao.execute(sql_update_result, (result_id,), commit=False)

    # Set result selector for current user
    sql_delete_selector = "DELETE FROM selector_rpt_main WHERE cur_user = current_user"
    dao.execute(sql_delete_selector, commit=False)

    sql_insert_selector = "INSERT INTO selector_rpt_main (result_id, cur_user) VALUES (%s, current_user)"
    dao.execute(sql_insert_selector, (result_id,), commit=False)

    # Clean null time values
    sql_clean_node_time = "UPDATE rpt_node SET time = '0:00' WHERE time = 'null' AND result_id = %s"
    dao.execute(sql_clean_node_time, (result_id,), commit=False)

    sql_clean_arc_time = "UPDATE rpt_arc SET time = '0:00' WHERE time = 'null' AND result_id = %s"
    dao.execute(sql_clean_arc_time, (result_id,), commit=False)



def _convert_from_si(
    value: float,
    unit_system: wntr.epanet.util.FlowUnits,
    param: wntr.epanet.util.HydParam,
    round_decimals: int = 2,
) -> float:
    """Convert value from SI to EPANET units."""
    return round(float(from_si(unit_system, value, param)), round_decimals)

# endregion

# region Export to FROST-Server Helper Functions

def _prepare_nodes_data(wn: wntr.network.WaterNetworkModel) -> List[Dict]:
    """Extract node data from WNTR water network model."""
    nodes_data = []
    for node_name, node in wn.nodes():
        node_type = tools_sensorthings.get_epanet_node_type(node)

        # Get coordinates
        coords = node.coordinates
        if coords is None or len(coords) < 2:
            tools_log.log_warning(f"Node {node_name} has no coordinates, skipping")
            continue

        nodes_data.append({
            'id': node_name,
            'type': node_type,
            'coordinates': (coords[0], coords[1])
        })

    return nodes_data


def _prepare_nodes_things_data(
    nodes_data: List[Dict], wn: wntr.network.WaterNetworkModel, results: wntr.sim.SimulationResults, sensor_ids: Dict[str, str],
    property_ids: Dict[str, str], transformer: Transformer, start_time: datetime,
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
        for prop in tools_sensorthings.EPANET_NODE_PROPERTIES:
            prop_config = tools_sensorthings.EPANET_OBSERVED_PROPERTIES[prop]
            try:
                if prop in results.node:
                    values = results.node[prop][node_id]
                else:
                    continue

                observations = []
                current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

                for timestamp, value in values.items():
                    observations.append({
                        "phenomenonTime": (start_time + timedelta(seconds=timestamp)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                        "result": float(value),
                        "resultTime": current_time
                    })

                datastream = {
                    "name": f"{prop_config['name']} at {node_id}",
                    "description": f"The {prop_config['name'].lower()} at EPANET {node_type} {node_id}",
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
            "description": f"EPANET {node_type} {node_id}",
            "Locations": [{
                "name": f"{node_id} Location",
                "description": f"Location of EPANET {node_type} {node_id}",
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


def _prepare_links_data(wn: wntr.network.WaterNetworkModel) -> List[Dict]:
    """Extract link data from WNTR water network model."""
    links_data = []

    for link_name, link in wn.links():
        link_type = tools_sensorthings.get_epanet_link_type(link)

        links_data.append({
            'id': link_name,
            'type': link_type
        })

    return links_data


def _prepare_links_things_data(
    links_data: List[Dict], results: wntr.sim.SimulationResults, sensor_ids: Dict[str, str],
    property_ids: Dict[str, str], wn: wntr.network.WaterNetworkModel, transformer: Transformer, start_time: datetime,
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

        link = wn.get_link(link_id)
        vertices = _get_geometry_from_link(link)

        transformed_vertices = []
        for x, y in vertices:
            lon, lat = transformer.transform(x, y)
            transformed_vertices.append([lon, lat])

        datastreams = []
        for prop in tools_sensorthings.EPANET_LINK_PROPERTIES:
            prop_config = tools_sensorthings.EPANET_OBSERVED_PROPERTIES[prop]
            try:
                if prop in results.link:
                    values = results.link[prop][link_id]
                else:
                    continue

                observations = []
                current_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

                for timestamp, value in values.items():
                    observations.append({
                        "phenomenonTime": (start_time + timedelta(seconds=timestamp)).strftime('%Y-%m-%dT%H:%M:%SZ'),
                        "result": float(value),
                        "resultTime": current_time
                    })

                datastream = {
                    "name": f"{prop_config['name']} at {link_id}",
                    "description": f"The {prop_config['name'].lower()} at EPANET {link_type} {link_id}",
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
            "description": f"EPANET {link_type} {link_id}",
            "Locations": [{
                "name": f"{link_id} Location",
                "description": f"Location of EPANET {link_type} {link_id}",
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


def _get_geometry_from_link(link: wntr.network.Link) -> list[tuple[float, float]]:
    """Get geometry coordinates for a link including vertices."""
    start_node = link.start_node
    end_node = link.end_node

    # Check if nodes have coordinates
    if start_node.coordinates is None or len(start_node.coordinates) < 2:
        tools_log.log_warning(
            f"Link {link.name}: start node {start_node.name} has no coordinates"
        )
        return []
    if end_node.coordinates is None or len(end_node.coordinates) < 2:
        tools_log.log_warning(
            f"Link {link.name}: end node {end_node.name} has no coordinates"
        )
        return []

    start_coords = (start_node.coordinates[0], start_node.coordinates[1])
    end_coords = (end_node.coordinates[0], end_node.coordinates[1])

    # Get vertices if they exist (link has vertices property)
    vertices = []
    if hasattr(link, 'vertices') and link.vertices is not None:
        # WNTR stores vertices as a list of (x, y) tuples or lists
        for v in link.vertices:
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                vertices.append((float(v[0]), float(v[1])))

    # Combine start node, vertices, and end node
    coordinates = []
    coordinates.append(start_coords)
    coordinates.extend(vertices)
    coordinates.append(end_coords)

    return coordinates

# endregion
