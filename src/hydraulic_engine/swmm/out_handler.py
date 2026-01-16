"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
"""
# -*- coding: utf-8 -*-
from typing import Dict, List, Optional
from datetime import datetime, timezone
from pyproj import Transformer
from swmm_api.output_file import SwmmOutput
from swmm_api.input_file import SwmmInput
from swmm_api.input_file.section_labels import COORDINATES, VERTICES

from .file_handler import SwmmResultHandler, SwmmFileHandler
from .inp_handler import SwmmInpHandler
from ..utils import tools_log
from ..utils.tools_api import get_api_client, HeFrostClient
from ..utils import tools_sensorthings


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

    def export_to_database(self) -> bool:
        """Export simulation results to database."""
        # TODO: Implement export to database
        tools_log.log_warning("Export to database not yet implemented")
        return False


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
            tools_log.log_error("No FROST client available")
            return False

        if not self.is_loaded():
            tools_log.log_error("No OUT file loaded")
            return False

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
            tools_log.log_error("No INP file loaded")
            return False

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
                tools_log.log_warning(f"Warning: Could not process {prop} for {node_id}: {e}")

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
                tools_log.log_warning(f"Warning: Could not process {prop} for {link_id}: {e}")

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

    return things_data


def _get_geometry_from_link(inp, link) -> list[tuple[float, float]]:
    """Get geometry coordinates for a link including vertices."""
    from_node = link.from_node
    if from_node not in inp[COORDINATES]:
        return []
    to_node = link.to_node
    if to_node not in inp[COORDINATES]:
        return []

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