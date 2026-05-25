# Hydraulic Engine

| | |
| --- | --- |
| Testing | [![CI - Test](https://github.com/Giswater/hydraulic_engine/actions/workflows/publish-to-pypi.yml/badge.svg)](https://github.com/Giswater/hydraulic_engine/actions/workflows/publish-to-pypi.yml) |
| Package | [![PyPI Latest Release](https://img.shields.io/pypi/v/hydraulic_engine.svg)](https://pypi.org/project/hydraulic_engine/) [![PyPI Downloads](https://img.shields.io/pypi/dm/hydraulic_engine.svg?label=PyPI%20downloads)](https://pypi.org/project/hydraulic_engine/) |
| Meta | [![License - GNU GPL3](https://img.shields.io/pypi/l/hydraulic_engine.svg)](https://github.com/Giswater/hydraulic_engine/blob/main/LICENSE) |


A Python package for managing hydraulic calculation actions: EPANET/SWMM simulations, RPT file imports, and more.

## Features

- **Run SWMM simulations**: Execute Storm Water Management Model simulations
- **Run EPANET simulations**: Execute water distribution network simulations
- **Parse INP files**: Read and modify SWMM/EPANET input files
- **Parse RPT files**: Read and analyze simulation results
- **Multiple database support**: PostgreSQL (psycopg3), SQLite, and GeoPackage

## Installation

### From PyPI

```bash
pip install hydraulic-engine
```

### From source

```bash
git clone https://github.com/bgeo-gis/hydraulic-engine.git
cd hydraulic-engine
pip install -e .
```

### Development installation

```bash
pip install -e ".[dev]"
```

## Quick Start

### Running a SWMM Simulation

```python
from hydraulic_engine.swmm import SwmmRunner

runner = SwmmRunner(
    inp_path="drainage_model.inp",
    rpt_path="results.rpt",
    out_path="results.out",
)
result = runner.run()

if result.status.value == "success":
    print(f"Simulation completed in {result.duration_seconds:.2f}s")
    print(f"RPT file: {result.rpt_path}")
else:
    print(f"Errors: {result.errors}")
```

### Running an EPANET Simulation

```python
from hydraulic_engine.epanet import EpanetRunner

runner = EpanetRunner(
    inp_path="water_network.inp",
    rpt_path="results.rpt",
    bin_path="results.bin",
)
result = runner.run()

if result.status.value == "success":
    print(f"Simulation completed in {result.duration_seconds:.2f}s")
```

### Reading SWMM INP Files

```python
from hydraulic_engine.swmm import SwmmInpHandler

handler = SwmmInpHandler()
handler.load_file("model.inp")

summary = handler.get_summary()
print(f"Junctions: {summary['counts']['junctions']}")
print(f"Conduits: {summary['counts']['conduits']}")

junctions = handler.get_junctions()
conduits = handler.get_conduits()

handler.write("modified_model.inp")
```

### Reading SWMM Results

```python
from hydraulic_engine.swmm import SwmmRptHandler

handler = SwmmRptHandler()
handler.load_file("results.rpt")

node_depths = handler.get_node_depth_summary()
link_flows = handler.get_link_flow_summary()
```

### Progress Tracking

```python
from hydraulic_engine.swmm import SwmmRunner

def on_progress(progress: int, message: str):
    print(f"[{progress}%] {message}")

runner = SwmmRunner(inp_path="model.inp", progress_callback=on_progress)
result = runner.run()
```

## Database Connection

The package supports database connections for storing/retrieving model data.

### PostgreSQL Connection

```python
import hydraulic_engine as he

conn = he.create_pg_connection(
    host="localhost",
    port=5432,
    dbname="hydraulic_db",
    user="user",
    password="pass",
    schema="my_schema",
)

rows = conn.get_rows("SELECT * FROM nodes")

he.close_connection()
```

### GeoPackage Connection

```python
import hydraulic_engine as he

conn = he.create_gpkg_connection("project.gpkg")

rows = conn.get_rows("SELECT * FROM conduits")

he.close_connection()
```

## Package Structure

```
hydraulic-engine/
├── src/
│   └── hydraulic_engine/
│       ├── __init__.py
│       ├── exceptions.py
│       ├── config/
│       │   └── config.py
│       ├── epanet/
│       │   ├── runner.py            # Run EPANET simulations
│       │   ├── inp_handler.py       # Parse/write EPANET INP files
│       │   ├── bin_handler.py       # Parse EPANET binary result files
│       │   ├── file_handler.py
│       │   └── models.py
│       ├── swmm/
│       │   ├── runner.py            # Run SWMM simulations
│       │   ├── inp_handler.py       # Parse/write SWMM INP files
│       │   ├── rpt_handler.py       # Parse SWMM RPT files
│       │   ├── out_handler.py       # Parse SWMM OUT files
│       │   ├── file_handler.py
│       │   └── models.py
│       └── utils/
│           ├── tools_log.py
│           ├── tools_db.py
│           ├── tools_api.py
│           ├── tools_os.py
│           ├── tools_config.py
│           └── tools_sensorthings.py
├── tests/
├── pyproject.toml
└── README.md
```

## API Reference

### SWMM Classes

| Class | Description |
|-------|-------------|
| `SwmmRunner` | Run SWMM simulations |
| `SwmmInpHandler` | Read/write SWMM INP files |
| `SwmmRptHandler` | Parse SWMM RPT result files |
| `SwmmOutHandler` | Parse SWMM OUT result files |

### EPANET Classes

| Class | Description |
|-------|-------------|
| `EpanetRunner` | Run EPANET simulations |
| `EpanetInpHandler` | Read/write EPANET INP files |
| `EpanetBinHandler` | Parse EPANET BIN result files |

### Connection Functions

| Function | Description |
|----------|-------------|
| `create_pg_connection(...)` | Create PostgreSQL connection |
| `create_gpkg_connection(gpkg_path)` | Create GeoPackage connection |
| `create_sqlite_connection(db_path)` | Create SQLite connection |
| `get_connection()` | Get current default connection |
| `close_connection()` | Close default connection |

## Dependencies

- Python >= 3.9
- pyswmm >= 2.0.0 (SWMM simulation engine)
- swmm-api >= 0.4.31 (INP/RPT file parsing)
- wntr >= 1.2.0 (EPANET simulations)
- psycopg[binary] >= 3.1.0
- requests >= 2.28.0
- pyproj >= 3.6.0

## Development

### Running tests

```bash
pytest tests/
```

### Code formatting

```bash
black src/
ruff check src/
```

## License

GNU General Public License v3.0 or later - see [LICENSE](LICENSE).

## Authors

**BGEO** - [info@bgeo.es](mailto:info@bgeo.es)
