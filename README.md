# Hydraulic Engine

A Python package for managing hydraulic calculation actions: EPANET/SWMM simulations, RPT file imports, and more.

## Features

- **Run SWMM simulations**: Execute Storm Water Management Model simulations
- **Run EPANET simulations**: Execute water distribution network simulations
- **Parse INP files**: Read and modify SWMM/EPANET input files
- **Parse RPT files**: Read and analyze simulation results
- **Multiple database support**: PostgreSQL (psycopg3), SQLite, and GeoPackage

## Installation

### From PyPI (when published)

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
import hydraulic_engine as he

# Create runner
runner = he.SwmmRunner(inp_path="drainage_model.inp")

# Run simulation
result = runner.run()

# Check results
if result.status.value == "success":
    print(f"Simulation completed in {result.duration_seconds:.2f}s")
    print(f"RPT file: {result.rpt_path}")
else:
    print(f"Errors: {result.errors}")
```

### Running an EPANET Simulation

```python
import hydraulic_engine as he

# Create runner
runner = he.EpanetRunner(inp_path="water_network.inp")

# Run simulation
result = runner.run()

# Check results
if result.status.value == "success":
    print(f"Simulation completed in {result.duration_seconds:.2f}s")
```

### Reading SWMM INP Files

```python
import hydraulic_engine as he

# Create handler
handler = he.SwmmInpHandler()

# Read INP file
if handler.read("model.inp"):
    # Get model summary
    summary = handler.get_summary()
    print(f"Junctions: {summary['counts']['junctions']}")
    print(f"Conduits: {summary['counts']['conduits']}")

    # Get specific sections
    junctions = handler.get_junctions()
    conduits = handler.get_conduits()

    # Modify and save
    handler.write("modified_model.inp")
```

### Reading SWMM Results

```python
import hydraulic_engine as he

# Create handler
handler = he.SwmmRptHandler()

# Read RPT file
if handler.load_result("results.rpt"):
    # Get results
    node_depths = handler.get_node_depth_summary()
    link_flows = handler.get_link_flow_summary()
```

### Validating INP Files

```python
import hydraulic_engine as he

# Validate without running
runner = he.SwmmRunner()
validation = runner.validate_inp("model.inp")

if validation["valid"]:
    print(f"Model info: {validation['info']}")
else:
    print(f"Validation errors: {validation['errors']}")
```

### Progress Tracking

```python
import hydraulic_engine as he

def on_progress(progress: int, message: str):
    print(f"[{progress}%] {message}")

runner = he.SwmmRunner(progress_callback=on_progress)
result = runner.run("model.inp")
```

## Database Connection

The package supports database connections for storing/retrieving model data.

### PostgreSQL Connection

```python
import hydraulic_engine as he

# Create connection (becomes the default)
conn = he.create_pg_connection(
    host="localhost",
    port=5432,
    dbname="hydraulic_db",
    user="user",
    password="pass",
    schema="my_schema"
)

# Use connection
rows = conn.get_rows("SELECT * FROM nodes")

# Close when done
he.close_connection()
```

### GeoPackage Connection

```python
import hydraulic_engine as he

# Create connection
conn = he.create_gpkg_connection("project.gpkg")

# Query data
rows = conn.get_rows("SELECT * FROM conduits")

# Close when done
he.close_connection()
```

## Package Structure

```
hydraulic-engine/
├── src/
│   └── hydraulic_engine/
│       ├── __init__.py│
│       ├── config/
│       │   ├── config.py
│       ├── core/
│       │   ├── swmm/                    # SWMM-specific functionality
│       │   │   ├── runner.py            # Run SWMM simulations
│       │   │   ├── inp_handler.py       # Parse/write SWMM INP files
│       │   │   └── rpt_handler.py       # Parse SWMM RPT files
│       │   ├── epanet/                  # EPANET-specific functionality
│       │   │   ├── runner.py            # Run EPANET simulations
│       │   │   ├── inp_handler.py       # Parse/write EPANET INP files
│       │   │   └── rpt_handler.py       # Parse EPANET RPT files
│       │   └── utils/                   # Shared utilities
│       │       ├── tools_log.py
│       │       ├── tools_db.py
│       │       └── tools_config.py
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

### EPANET Classes

| Class | Description |
|-------|-------------|
| `EpanetRunner` | Run EPANET simulations |
| `EpanetInpHandler` | Read/write EPANET INP files |
| `EpanetRptHandler` | Parse EPANET RPT result files |

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
- swmm-api >= 0.4.60 (INP/RPT file parsing)
- wntr >= 1.0.0 (EPANET simulations)
- pandas >= 2.0.0
- numpy >= 1.24.0
- psycopg[binary] >= 3.1.0

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
