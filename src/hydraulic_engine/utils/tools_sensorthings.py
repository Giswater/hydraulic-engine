"""
This file is part of Hydraulic Engine
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

SensorThings API helper functions for hydraulic data export.
High-level functions built on top of HeFrostClient.
"""
# -*- coding: utf-8 -*-
import time
import wntr
import os

from typing import Dict, List, Optional, Tuple, Literal
from swmm_api.input_file import SwmmInput

from .tools_api import get_api_client, HeFrostClient
from . import tools_log


# region SWMM

# Observed properties configuration - single source of truth
SWMM_OBSERVED_PROPERTIES = {
    # Node properties
    'head': {
        'name': 'Head',
        'description': 'Node head',
        'unit_symbol': 'm',
        'unit': {'name': 'Meter', 'symbol': 'm', 'definition': 'ucum:m'}
    },
    'depth': {
        'name': 'Depth',
        'description': 'Node depth',
        'unit_symbol': 'm',
        'unit': {'name': 'Meter', 'symbol': 'm', 'definition': 'ucum:m'}
    },
    'volume': {
        'name': 'Volume',
        'description': 'Node volume',
        'unit_symbol': 'm³',
        'unit': {'name': 'Cubic meters', 'symbol': 'm³', 'definition': 'ucum:m3'}
    },
    'lateral_inflow': {
        'name': 'Lateral Inflow',
        'description': 'Node lateral inflow',
        'unit_symbol': 'm³/s',
        'unit': {'name': 'Cubic meters per second', 'symbol': 'm³/s', 'definition': 'ucum:m3/s'}
    },
    'total_inflow': {
        'name': 'Total Inflow',
        'description': 'Node total inflow',
        'unit_symbol': 'm³/s',
        'unit': {'name': 'Cubic meters per second', 'symbol': 'm³/s', 'definition': 'ucum:m3/s'}
    },
    'flooding': {
        'name': 'Flooding',
        'description': 'Node flooding',
        'unit_symbol': 'm³/s',
        'unit': {'name': 'Cubic meters per second', 'symbol': 'm³/s', 'definition': 'ucum:m3/s'}
    },
    # Link properties
    'flow': {
        'name': 'Flow',
        'description': 'Link flow',
        'unit_symbol': 'm³/s',
        'unit': {'name': 'Cubic meters per second', 'symbol': 'm³/s', 'definition': 'ucum:m3/s'}
    },
    'velocity': {
        'name': 'Velocity',
        'description': 'Link velocity',
        'unit_symbol': 'm/s',
        'unit': {'name': 'Meters per second', 'symbol': 'm/s', 'definition': 'ucum:m/s'}
    },
    'capacity': {
        'name': 'Capacity',
        'description': 'Link capacity',
        'unit_symbol': 'm³',
        'unit': {'name': 'Cubic meters', 'symbol': 'm³', 'definition': 'ucum:m3'}
    }
}

# Property keys by entity type
SWMM_NODE_PROPERTIES = ['head', 'depth', 'volume', 'lateral_inflow', 'total_inflow', 'flooding']
SWMM_LINK_PROPERTIES = ['flow', 'depth', 'velocity', 'volume', 'capacity']
SWMM_NODE_TYPES = ['JUNCTION', 'OUTFALL', 'STORAGE', 'DIVIDER']

# endregion

# region EPANET

# Observed properties configuration - single source of truth
EPANET_OBSERVED_PROPERTIES = {
    # Node properties
    'pressure': {
        'name': 'Pressure',
        'description': 'Node pressure',
        'unit_symbol': 'm',
        'unit': {'name': 'Meter', 'symbol': 'm', 'definition': 'ucum:m'}
    },
    'head': {
        'name': 'Head',
        'description': 'Node head',
        'unit_symbol': 'm',
        'unit': {'name': 'Meter', 'symbol': 'm', 'definition': 'ucum:m'}
    },
    'demand': {
        'name': 'Demand',
        'description': 'Node demand',
        'unit_symbol': 'm³/s',
        'unit': {'name': 'Cubic meters per second', 'symbol': 'm³/s', 'definition': 'ucum:m3/s'}
    },
    'quality': {
        'name': 'Quality',
        'description': 'Water quality',
        'unit_symbol': 'mg/L',
        'unit': {'name': 'Milligrams per liter', 'symbol': 'mg/L', 'definition': 'ucum:mg/L'}
    },
    # Link properties
    'flowrate': {
        'name': 'Flow Rate',
        'description': 'Link flow rate',
        'unit_symbol': 'm³/s',
        'unit': {'name': 'Cubic meters per second', 'symbol': 'm³/s', 'definition': 'ucum:m3/s'}
    },
    'velocity': {
        'name': 'Velocity',
        'description': 'Link velocity',
        'unit_symbol': 'm/s',
        'unit': {'name': 'Meters per second', 'symbol': 'm/s', 'definition': 'ucum:m/s'}
    },
    'headloss': {
        'name': 'Head Loss',
        'description': 'Link head loss',
        'unit_symbol': 'm',
        'unit': {'name': 'Meter', 'symbol': 'm', 'definition': 'ucum:m'}
    },
    'status': {
        'name': 'Status',
        'description': 'Link status',
        'unit_symbol': 'dimensionless',
        'unit': {'name': 'Dimensionless', 'symbol': '', 'definition': 'ucum:1'}
    },
    'setting': {
        'name': 'Setting',
        'description': 'Link setting',
        'unit_symbol': 'dimensionless',
        'unit': {'name': 'Dimensionless', 'symbol': '', 'definition': 'ucum:1'}
    },
    'friction_factor': {
        'name': 'Friction Factor',
        'description': 'Pipe friction factor',
        'unit_symbol': 'dimensionless',
        'unit': {'name': 'Dimensionless', 'symbol': '', 'definition': 'ucum:1'}
    },
    'reaction_rate': {
        'name': 'Reaction Rate',
        'description': 'Link reaction rate',
        'unit_symbol': 'mg/L/day',
        'unit': {'name': 'Milligrams per liter per day', 'symbol': 'mg/L/day', 'definition': 'ucum:mg.L-1.d-1'}
    }
}

# Property keys by entity type
EPANET_NODE_PROPERTIES = ['pressure', 'head', 'demand', 'quality']
EPANET_LINK_PROPERTIES = [
    'quality', 'flowrate', 'velocity', 'headloss', 'status', 'setting',
    'friction_factor', 'reaction_rate'
]
EPANET_NODE_TYPES = ['JUNCTION', 'RESERVOIR', 'TANK']

# endregion

def get_node_properties(engine: Literal['swmm', 'epanet']) -> List[str]:
    if engine == 'swmm':
        return SWMM_NODE_PROPERTIES
    elif engine == 'epanet':
        return EPANET_NODE_PROPERTIES


def get_link_properties(engine: Literal['swmm', 'epanet']) -> List[str]:
    if engine == 'swmm':
        return SWMM_LINK_PROPERTIES
    elif engine == 'epanet':
        return EPANET_LINK_PROPERTIES


def get_observed_property_config(prop_key: str, engine: Literal['swmm', 'epanet']) -> Dict:
    if engine == 'swmm':
        return SWMM_OBSERVED_PROPERTIES[prop_key]
    elif engine == 'epanet':
        return EPANET_OBSERVED_PROPERTIES[prop_key]


def get_entity_id(url: str) -> str:
    """
    Extract entity ID from a SensorThings API URL.
    
    :param url: Entity URL (e.g., "http://localhost/Things(1)")
    :return: Entity ID
    """
    return url.split('(')[-1].strip(')')


def geometry_changed(old_location: Dict, new_location: Dict) -> bool:
    """
    Check if location geometry has changed.
    
    :param old_location: Old location data
    :param new_location: New location data
    :return: True if geometry changed
    """
    if not old_location:
        return True
    old_geom = old_location.get('location', {})
    return old_geom != new_location


def create_thing_with_location(
    name: str,
    description: str,
    location_data: Dict,
    properties: Optional[Dict] = None,
    client: Optional[HeFrostClient] = None
) -> Optional[str]:
    """
    Create a Thing with its Location using deep insert.
    
    :param name: Thing name
    :param description: Thing description
    :param location_data: GeoJSON location
    :param properties: Additional properties
    :param client: FROST client (uses default if None)
    :return: Thing URL or None
    """
    if client is None:
        client = get_api_client()

    if not client or not isinstance(client, HeFrostClient):
        tools_log.log_error("No FROST client available")
        return None

    thing_data = {
        "name": name,
        "description": description,
        "properties": properties or {},
        "Locations": [{
            "name": f"{name} Location",
            "description": f"Location of {name}",
            "encodingType": "application/geo+json",
            "location": location_data
        }]
    }

    return client.create_entity('Things', thing_data)


def create_sensor(
    name: str,
    description: str,
    properties: Optional[Dict] = None,
    client: Optional[HeFrostClient] = None
) -> Optional[str]:
    """
    Create a Sensor.
    
    :param name: Sensor name
    :param description: Sensor description
    :param properties: Additional properties
    :param client: FROST client (uses default if None)
    :return: Sensor URL or None
    """
    if client is None:
        client = get_api_client()

    if not client or not isinstance(client, HeFrostClient):
        tools_log.log_error("No FROST client available")
        return None

    sensor_data = {
        "name": name,
        "description": description,
        "properties": properties or {},
        "encodingType": "application/pdf",
        "metadata": description
    }

    return client.create_entity('Sensors', sensor_data)


def create_observed_property(
    name: str,
    description: str,
    unit: str,
    client: Optional[HeFrostClient] = None
) -> Optional[str]:
    """
    Create an ObservedProperty.
    
    :param name: Property name
    :param description: Property description
    :param unit: Unit of measurement
    :param client: FROST client (uses default if None)
    :return: ObservedProperty URL or None
    """
    if client is None:
        client = get_api_client()

    if not client or not isinstance(client, HeFrostClient):
        tools_log.log_error("No FROST client available")
        return None

    property_data = {
        "name": name,
        "description": description,
        "definition": f"http://example.org/def/{name.lower().replace(' ', '_')}"
    }

    return client.create_entity('ObservedProperties', property_data)


def create_datastream(
    name: str,
    description: str,
    unit_of_measurement: Dict,
    thing_id: str,
    sensor_id: str,
    property_id: str,
    observations: Optional[List[Dict]] = None,
    client: Optional[HeFrostClient] = None
) -> Optional[str]:
    """
    Create a Datastream with optional Observations.
    
    :param name: Datastream name
    :param description: Datastream description
    :param unit_of_measurement: Unit dict with name, symbol, definition
    :param thing_id: Thing ID
    :param sensor_id: Sensor ID
    :param property_id: ObservedProperty ID
    :param observations: List of observations to create with datastream
    :param client: FROST client (uses default if None)
    :return: Datastream URL or None
    """
    if client is None:
        client = get_api_client()

    if not client or not isinstance(client, HeFrostClient):
        tools_log.log_error("No FROST client available")
        return None

    datastream_data = {
        "name": name,
        "description": description,
        "observationType": "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement",
        "unitOfMeasurement": unit_of_measurement,
        "Thing": {"@iot.id": thing_id},
        "Sensor": {"@iot.id": sensor_id},
        "ObservedProperty": {"@iot.id": property_id}
    }

    if observations:
        datastream_data["Observations"] = observations

    return client.create_entity('Datastreams', datastream_data)


def get_all_things_with_locations(
    client: Optional[HeFrostClient] = None
) -> Dict[str, Dict]:
    """
    Fetch all Things with their Locations expanded.
    Returns a dict keyed by Thing name for O(1) lookup.
    
    :param client: FROST client (uses default if None)
    :return: Dict mapping Thing name to Thing data
    """
    if client is None:
        client = get_api_client()

    if not client or not isinstance(client, HeFrostClient):
        tools_log.log_error("No FROST client available")
        return {}

    things_cache = {}
    things = client.get_entities('Things', expand='Locations')

    if things:
        for thing in things:
            things_cache[thing['name']] = {
                'id': thing['@iot.id'],
                'properties': thing.get('properties', {}),
                'Locations': thing.get('Locations', [])
            }

    return things_cache


def get_all_observed_properties(
    client: Optional[HeFrostClient] = None
) -> Dict[str, str]:
    """
    Fetch all ObservedProperties.
    Returns a dict keyed by name with ID as value.
    
    :param client: FROST client (uses default if None)
    :return: Dict mapping property name to property ID
    """
    if client is None:
        client = get_api_client()

    if not client or not isinstance(client, HeFrostClient):
        tools_log.log_error("No FROST client available")
        return {}

    obs_props_cache = {}
    properties = client.get_entities('ObservedProperties')

    if properties:
        for prop in properties:
            obs_props_cache[prop['name']] = prop['@iot.id']

    return obs_props_cache


def prepare_thing_requests(
    thing_data: Dict,
    things_cache: Dict[str, Dict],
    request_id_counter: List[int]
) -> Tuple[List[Dict], str]:
    """
    Prepare batch request operations for a Thing.

    :param thing_data: Thing data with name, Locations, Datastreams, properties
    :param things_cache: Pre-fetched cache of existing Things
    :param request_id_counter: Mutable counter [int] for unique request IDs
    :return: Tuple of (list of batch request dicts, thing_id or reference)
    """
    thing_name = thing_data['name']
    new_location = thing_data['Locations'][0]['location']
    batch_requests = []

    def next_id():
        request_id_counter[0] += 1
        return str(request_id_counter[0])

    if thing_name in things_cache:
        # Thing exists - prepare update operations
        cached = things_cache[thing_name]
        thing_id = cached['id']

        # PATCH Thing to update state to operative
        batch_requests.append({
            "id": next_id(),
            "method": "patch",
            "url": f"Things({thing_id})",
            "body": {"properties": {**cached.get('properties', {}), "state": "operative"}}
        })

        # PATCH Location if geometry changed
        if cached['Locations']:
            old_location = cached['Locations'][0]
            if geometry_changed(old_location, new_location):
                location_id = old_location['@iot.id']
                batch_requests.append({
                    "id": next_id(),
                    "method": "patch",
                    "url": f"Locations({location_id})",
                    "body": {"location": new_location}
                })

        # POST each Datastream to existing Thing
        for ds in thing_data.get('Datastreams', []):
            ds_copy = ds.copy()
            ds_copy['Thing'] = {"@iot.id": thing_id}
            batch_requests.append({
                "id": next_id(),
                "method": "post",
                "url": "Datastreams",
                "body": ds_copy
            })

        return batch_requests, thing_id
    else:
        # Thing doesn't exist - create with deep insert
        thing_data_copy = thing_data.copy()
        thing_data_copy['properties'] = {**thing_data_copy.get('properties', {}), "state": "operative"}

        thing_ref = f"thing_{thing_name}"
        batch_requests.append({
            "id": thing_ref,
            "method": "post",
            "url": "Things",
            "body": thing_data_copy
        })

        return batch_requests, f"${thing_ref}"


def process_things_batch(
    things_data: List[Dict],
    things_cache: Optional[Dict[str, Dict]] = None,
    batch_size: int = 50,
    max_workers: int = 4,
    client: Optional[HeFrostClient] = None
) -> bool:
    """
    Process multiple Things using batch requests with concurrent workers.

    :param things_data: List of Thing data dicts with name, Locations, Datastreams, properties
    :param things_cache: Pre-fetched cache of existing Things (will fetch if None)
    :param batch_size: Maximum operations per batch request (default 50, keep low for deep inserts)
    :param max_workers: Number of concurrent batch requests (default 4)
    :param client: FROST client (uses default if None)
    :return: True if successful
    """
    if client is None:
        client = get_api_client()

    if not client or not isinstance(client, HeFrostClient):
        tools_log.log_error("No FROST client available")
        return False

    # Fetch cache if not provided
    if things_cache is None:
        tools_log.log_info("Fetching existing Things from FROST-Server...")
        things_cache = get_all_things_with_locations(client)

    all_requests = []
    request_id_counter = [0]

    new_count = 0
    update_count = 0
    total_datastreams = 0

    tools_log.log_info(f"Preparing batch requests for {len(things_data)} Things...")
    prep_start = time.time()

    for thing_data in things_data:
        thing_name = thing_data['name']
        is_new = thing_name not in things_cache

        requests_for_thing, _ = prepare_thing_requests(thing_data, things_cache, request_id_counter)
        all_requests.extend(requests_for_thing)
        total_datastreams += len(thing_data.get('Datastreams', []))

        if is_new:
            new_count += 1
        else:
            update_count += 1

    prep_time = time.time() - prep_start

    if not all_requests:
        tools_log.log_info("No requests to process")
        return True

    num_batches = (len(all_requests) + batch_size - 1) // batch_size
    tools_log.log_info(f"Prepared {len(all_requests)} operations in {prep_time:.2f}s")
    tools_log.log_info(f"  Things: {new_count} new, {update_count} updates")
    tools_log.log_info(f"  Datastreams: {total_datastreams}")
    tools_log.log_info(f"  Batches: {num_batches} (batch_size={batch_size}, max_workers={max_workers})")
    tools_log.log_info("Sending batches...")

    try:
        send_start = time.time()
        responses = client.batch_request(all_requests, batch_size, max_workers)

        if responses is None:
            tools_log.log_error("Batch request failed")
            return False

        send_time = time.time() - send_start

        # Count successes and failures
        success_count = sum(1 for r in responses if 200 <= r.get('status', 0) < 300)
        error_count = len(responses) - success_count

        total_time = prep_time + send_time
        ops_per_sec = len(all_requests) / send_time if send_time > 0 else 0

        tools_log.log_info(f"Batch complete: {success_count} succeeded, {error_count} failed")
        tools_log.log_info(f"  Send time: {send_time:.2f}s ({ops_per_sec:.1f} ops/sec)")
        tools_log.log_info(f"  Total time: {total_time:.2f}s")

        # Log errors if any (limit to first 10)
        error_responses = [r for r in responses if r.get('status', 0) >= 400]
        if error_responses:
            tools_log.log_warning(f"  First {min(10, len(error_responses))} errors:")
            for resp in error_responses[:10]:
                error_msg = str(resp.get('body', ''))[:100]
                tools_log.log_warning(f"    Request {resp.get('id')}: {resp.get('status')} - {error_msg}")

        return error_count == 0

    except Exception as e:
        tools_log.log_error(f"Error in batch request: {e}")
        return False


def mark_obsolete_things(
    things_cache: Dict[str, Dict],
    active_feature_ids: set,
    batch_size: int = 100,
    max_workers: int = 4,
    client: Optional[HeFrostClient] = None
) -> bool:
    """
    Mark Things not in the active feature set as obsolete using batch requests.
    Uses the pre-fetched cache, no additional queries needed.
    
    :param things_cache: Pre-fetched cache of existing Things
    :param active_feature_ids: Set of active feature IDs (e.g., from INP file)
    :param batch_size: Maximum operations per batch request
    :param max_workers: Number of concurrent batch requests (default 4)
    :param client: FROST client (uses default if None)
    :return: True if successful
    """
    if client is None:
        client = get_api_client()

    if not client or not isinstance(client, HeFrostClient):
        tools_log.log_error("No FROST client available")
        return False

    obsolete_things = []
    for thing_name, thing_data in things_cache.items():
        if thing_name not in active_feature_ids:
            obsolete_things.append((thing_data['id'], thing_name, thing_data.get('properties', {})))

    if not obsolete_things:
        tools_log.log_info("No obsolete Things to mark")
        return True

    tools_log.log_info(f"Marking {len(obsolete_things)} Things as obsolete...")

    # Build batch requests
    batch_requests = []
    for i, (thing_id, thing_name, properties) in enumerate(obsolete_things):
        batch_requests.append({
            "id": str(i),
            "method": "patch",
            "url": f"Things({thing_id})",
            "body": {"properties": {**properties, "state": "obsolete"}}
        })

    try:
        responses = client.batch_request(batch_requests, batch_size, max_workers)

        if responses is None:
            tools_log.log_error("Batch request failed")
            return False

        success_count = sum(1 for r in responses if 200 <= r.get('status', 0) < 300)
        tools_log.log_info(f"Marked {success_count} Things as obsolete")
        return success_count == len(obsolete_things)

    except Exception as e:
        tools_log.log_error(f"Error marking Things as obsolete: {e}")
        return False


def delete_all_entities(
    batch_size: int = 100,
    max_workers: int = 4,
    client: Optional[HeFrostClient] = None
) -> bool:
    """
    Delete all entities from the FROST-Server database using batch requests.

    :param batch_size: Maximum number of delete operations per batch request
    :param max_workers: Number of concurrent batch requests (default 4)
    :param client: FROST client (uses default if None)
    :return: True if successful
    """
    if client is None:
        client = get_api_client()

    if not client or not isinstance(client, HeFrostClient):
        tools_log.log_error("No FROST client available")
        return False

    entities = ['Things', 'Locations', 'Sensors', 'ObservedProperties']

    for entity in entities:
        try:
            # Get all entity IDs
            all_entities = client.get_entities(entity)

            if not all_entities:
                tools_log.log_info(f"No {entity} to delete")
                continue

            entity_ids = [item['@iot.id'] for item in all_entities]

            # Build batch delete requests
            delete_requests = []
            for i, entity_id in enumerate(entity_ids):
                delete_requests.append({
                    "id": str(i),
                    "method": "delete",
                    "url": f"{entity}({entity_id})"
                })

            # Send batch delete
            tools_log.log_info(f"Deleting {len(entity_ids)} {entity} using batch requests...")
            responses = client.batch_request(delete_requests, batch_size, max_workers)

            if responses is None:
                tools_log.log_error(f"Failed to delete {entity}")
                continue

            success_count = sum(1 for r in responses if 200 <= r.get('status', 0) < 300)
            tools_log.log_info(f"Completed deletion of {success_count}/{len(entity_ids)} {entity} entities")

        except Exception as e:
            tools_log.log_error(f"Error processing {entity} entities: {e}")
            return False

    return True


def get_or_create_observed_properties(
    obs_props_cache: Dict[str, str],
    engine: Literal['swmm', 'epanet'],
    client: Optional[HeFrostClient] = None
) -> Dict[str, str]:
    """
    Get or create observed properties using the pre-fetched cache.
    Only creates properties that don't already exist.
    Returns a dict mapping property keys to IDs.
    """
    property_ids = {}

    for prop_key in set(get_node_properties(engine) + get_link_properties(engine)):
        prop_config = get_observed_property_config(prop_key, engine)
        prop_name = prop_config['name']

        if prop_name in obs_props_cache:
            # Use existing property
            property_ids[prop_key] = obs_props_cache[prop_name]
            tools_log.log_info(f"Using existing ObservedProperty: {prop_name}")
        else:
            # Create new property
            prop_url = create_observed_property(
                prop_name,
                prop_config['description'],
                prop_config['unit_symbol'],
                client=client
            )
            property_ids[prop_key] = get_entity_id(prop_url)
            tools_log.log_info(f"Created ObservedProperty: {prop_name}")

    return property_ids


def create_simulation_sensor(
    result_id: str,
    network_type: Literal['EPANET', 'SWMM'],
    inp_file: str,
    client: Optional[HeFrostClient] = None
) -> Dict[str, str]:
    """Create a new sensor for this simulation run."""
    inp_filename = os.path.basename(inp_file)

    sensor_properties = {
        "simulated": True,
        "network_type": network_type,
        "inp_file": inp_file,
        "inp_filename": inp_filename,
        "result_id": result_id
    }
    sensor_url = create_sensor(
        f"Simulation {result_id}",
        f"{network_type} Simulated Data ({inp_filename})",
        properties=sensor_properties,
        client=client
    )
    sensor_ids = {'simulated': get_entity_id(sensor_url)}
    tools_log.log_info(f"Created Sensor: Simulation {result_id}")

    return sensor_ids


def get_swmm_node_type(node: str, inp_data: SwmmInput) -> str:
    """Get the type of a SWMM node from the input data."""
    node_type = 'JUNCTION'  # Default type
    if 'OUTFALLS' in inp_data and node in inp_data['OUTFALLS']:
        node_type = 'OUTFALL'
    elif 'STORAGE' in inp_data and node in inp_data['STORAGE']:
        node_type = 'STORAGE'
    elif 'DIVIDERS' in inp_data and node in inp_data['DIVIDERS']:
        node_type = 'DIVIDER'
    elif 'JUNCTIONS' in inp_data and node in inp_data['JUNCTIONS']:
        node_type = 'JUNCTION'

    return node_type


def get_epanet_node_type(node: wntr.network.Node) -> str:
    """Get the type of a EPANET node from the input data."""
    if isinstance(node, wntr.network.Junction):
        return 'JUNCTION'
    elif isinstance(node, wntr.network.Reservoir):
        return 'RESERVOIR'
    elif isinstance(node, wntr.network.Tank):
        return 'TANK'
    return 'UNKNOWN'


def get_swmm_link_type(link: str, inp_data: SwmmInput) -> str:
    """Get the type of a SWMM link from the input data."""
    link_type = 'CONDUIT'  # Default type
    if 'PUMPS' in inp_data and link in inp_data['PUMPS']:
        link_type = 'PUMP'
    elif 'ORIFICES' in inp_data and link in inp_data['ORIFICES']:
        link_type = 'ORIFICE'
    elif 'WEIRS' in inp_data and link in inp_data['WEIRS']:
        link_type = 'WEIR'
    elif 'OUTLETS' in inp_data and link in inp_data['OUTLETS']:
        link_type = 'OUTLET'

    return link_type


def get_epanet_link_type(link: wntr.network.Link) -> str:
    """Get the type of a EPANET link from the input data."""
    if isinstance(link, wntr.network.Pipe):
        return 'PIPE'
    elif isinstance(link, wntr.network.Pump):
        return 'PUMP'
    elif isinstance(link, wntr.network.Valve):
        return 'VALVE'
    return 'UNKNOWN'
