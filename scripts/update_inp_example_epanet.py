"""
Test script for updating an INP file for EPANET.
"""
import os
import sys

# Add the src directory to path for development
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import hydraulic_engine as he
from hydraulic_engine.utils import tools_log

from observed_data_generator import generate_observed_data

# =============================================================================
# CONFIGURATION - Update these values
# =============================================================================

# EPANET INP file path
INP_FILE = r""  # <-- Change this, e.g., r"C:\path\to\input\results.inp"

# Updated INP file path
INP_FILE_UPDATED = r""  # <-- Change this, e.g., r"C:\path\to\input\results_updated.inp"

# =============================================================================
# SCRIPT
# =============================================================================

def progress_callback(progress: int, message: str):
    """Callback to show simulation progress."""
    bar_length = 30
    filled = int(bar_length * progress / 100)
    bar = '█' * filled + '░' * (bar_length - filled)
    print(f"\r[{bar}] {progress:3d}% - {message}", end='', flush=True)
    if progress == 100:
        print()  # New line at the end


def main():
    print("=" * 60)
    print("HYDRAULIC ENGINE - Update INP Test Script for EPANET")
    print("=" * 60)

    # -------------------------------------------------------------------------
    # Initialize logger (logs will be in %APPDATA%/hydraulic_engine/log/)
    # -------------------------------------------------------------------------
    tools_log.set_logger("hydraulic_engine", min_log_level=10)  # 10=DEBUG
    print(f"\n[0] Logger initialized")
    print(f"    Log file: {he.config.logger.filepath if he.config.logger else 'N/A'}")

    # D-W - 2.5e-06
    # H-W - 0.0025

    # -------------------------------------------------------------------------
    # Step 1: Update INP file
    # -------------------------------------------------------------------------
    print(f"\n[1] Updating INP file...")

    inp_handler = he.epanet.EpanetInpHandler()
    inp_handler.load_file(INP_FILE)

    # Update INP file
    feature_settings = he.epanet.EpanetFeatureSettings()
    feature_settings.junctions = {
        "139": he.epanet.EpanetJunction(elevation=10.0, demand_list=[he.epanet.EpanetDemand(base_demand=10.0), he.epanet.EpanetDemand(base_demand=20.0)]),
    }

    options_settings = he.epanet.EpanetOptionsSettings(
        hydraulic=he.epanet.EpanetHydraulicOptions(specific_gravity=1.01)
    )

    inp_handler.update_inp_from_settings(feature_settings=feature_settings, options_settings=options_settings)
    inp_handler.write(INP_FILE_UPDATED)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)

    return 0 if os.path.exists(INP_FILE_UPDATED) else 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
