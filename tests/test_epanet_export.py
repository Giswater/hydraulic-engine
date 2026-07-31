"""
Copyright © 2026 by BGEO. All rights reserved.
The program is free software: you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.

EPANET export performance helper tests.
"""
# -*- coding: utf-8
from types import SimpleNamespace

import pandas as pd
import pytest
import wntr
from wntr.epanet.util import FlowUnits, HydParam, from_si

from hydraulic_engine.epanet.bin_handler import (
    _PreparedArcData,
    _PreparedNodeData,
    _convert_dataframe_from_si,
    _convert_from_si,
    _dataframe_metric_stats,
    _iter_node_records,
    _prepare_arc_data,
    _prepare_node_data,
    _seconds_to_time_str,
    _status_to_str,
)


class TestTimeConversion:
    def test_seconds_to_time_str(self):
        assert _seconds_to_time_str(0) == "0:00:00"
        assert _seconds_to_time_str(3661) == "1:01:01"
        assert _seconds_to_time_str(7200) == "2:00:00"


class TestUnitConversion:
    def test_convert_from_si_matches_dataframe_factor(self):
        unit_system = FlowUnits.GPM
        values = pd.DataFrame(
            [[1.0, 2.0], [3.0, 4.0]],
            index=[0, 3600],
            columns=["N1", "N2"],
        )
        converted_df = _convert_dataframe_from_si(values, unit_system, HydParam.Demand, 2)
        for time_sec in values.index:
            for node_id in values.columns:
                scalar = _convert_from_si(
                    values.loc[time_sec, node_id],
                    unit_system,
                    HydParam.Demand,
                    2,
                )
                assert scalar == converted_df.loc[time_sec, node_id]

    def test_from_si_is_linear_for_hydraulic_params(self):
        unit_system = FlowUnits.GPM
        for param in (
            HydParam.Demand,
            HydParam.Flow,
            HydParam.Pressure,
            HydParam.HydraulicHead,
            HydParam.Length,
            HydParam.PipeDiameter,
        ):
            single = from_si(unit_system, 1.0, param)
            double = from_si(unit_system, 2.0, param)
            assert double == pytest.approx(2 * single)


class TestDataframeMetricStats:
    def test_metric_stats_match_reference_implementation(self):
        df = pd.DataFrame(
            {
                "J1": [10.0, 30.0, 20.0],
                "J2": [5.0, 1.0, 3.0],
            },
            index=[0, 3600, 7200],
        )
        stats = _dataframe_metric_stats(df, round_decimals=2)

        assert stats["J1"]["max"] == 30.0
        assert stats["J1"]["min"] == 10.0
        assert stats["J1"]["avg"] == 20.0
        assert stats["J1"]["tmax"] == "1:00:00"
        assert stats["J1"]["tmin"] == "0:00:00"

        assert stats["J2"]["max"] == 5.0
        assert stats["J2"]["min"] == 1.0
        assert stats["J2"]["avg"] == 3.0
        assert stats["J2"]["tmax"] == "0:00:00"
        assert stats["J2"]["tmin"] == "1:00:00"

    def test_metric_stats_use_abs_when_requested(self):
        df = pd.DataFrame({"P1": [-10.0, 5.0, -20.0]}, index=[0, 3600, 7200])
        stats = _dataframe_metric_stats(df, round_decimals=2, use_abs=True)
        assert stats["P1"]["max"] == 20.0
        assert stats["P1"]["min"] == 5.0


class TestStatusMapping:
    def test_status_to_str(self):
        assert _status_to_str(0) == "CLOSED"
        assert _status_to_str(1) == "OPEN"
        assert _status_to_str(2) == "ACTIVE"
        assert _status_to_str(99) == "99"
        assert _status_to_str(None) is None


class TestIterNodeRecords:
    def test_iter_node_records_shape_and_values(self):
        prepared = _PreparedNodeData(
            node_ids=["J1", "J2"],
            time_strings=["0:00:00", "1:00:00"],
            top_elev={"J1": 100.0, "J2": 101.0},
            demand=pd.DataFrame([[1.0, 2.0], [3.0, 4.0]], index=[0, 3600], columns=["J1", "J2"]),
            head=pd.DataFrame([[10.0, 11.0], [12.0, 13.0]], index=[0, 3600], columns=["J1", "J2"]),
            press=pd.DataFrame([[20.0, 21.0], [22.0, 23.0]], index=[0, 3600], columns=["J1", "J2"]),
            quality=pd.DataFrame([[0.1, 0.2], [0.3, 0.4]], index=[0, 3600], columns=["J1", "J2"]),
        )

        records = list(_iter_node_records("result-1", prepared))
        assert len(records) == 4
        assert records[0] == ("result-1", "J1", "0:00:00", 100.0, 1.0, 10.0, 20.0, 0.1)
        assert records[-1] == ("result-1", "J2", "1:00:00", 101.0, 4.0, 13.0, 23.0, 0.4)


def _build_mock_inp_handler(unit_name: str = "GPM"):
    node_j1 = SimpleNamespace(elevation=100.0)
    node_j2 = SimpleNamespace(elevation=101.0)
    link_p1 = SimpleNamespace(length=1000.0, diameter=0.3)
    link_p2 = SimpleNamespace(length=500.0, diameter=0.2)

    wn = SimpleNamespace(
        nodes={"J1": node_j1, "J2": node_j2},
        links={"P1": link_p1, "P2": link_p2},
        options=SimpleNamespace(
            hydraulic=SimpleNamespace(inpfile_units=unit_name)
        ),
    )
    return SimpleNamespace(file_object=wn)


class TestPrepareExportData:
    def test_prepare_node_data_from_synthetic_results(self):
        results = SimpleNamespace(
            node={
                "demand": pd.DataFrame([[0.001, 0.002], [0.003, 0.004]], index=[0, 3600], columns=["J1", "J2"]),
                "head": pd.DataFrame([[50.0, 51.0], [52.0, 53.0]], index=[0, 3600], columns=["J1", "J2"]),
                "pressure": pd.DataFrame([[30.0, 31.0], [32.0, 33.0]], index=[0, 3600], columns=["J1", "J2"]),
                "quality": pd.DataFrame([[0.5, 0.6], [0.7, 0.8]], index=[0, 3600], columns=["J1", "J2"]),
            }
        )
        prepared = _prepare_node_data(results, _build_mock_inp_handler(), round_decimals=2)

        assert prepared.node_ids == ["J1", "J2"]
        assert prepared.time_strings == ["0:00:00", "1:00:00"]
        assert prepared.top_elev["J1"] == _convert_from_si(100.0, FlowUnits.GPM, HydParam.Elevation, 2)
        assert prepared.demand.loc[0, "J1"] == _convert_from_si(0.001, FlowUnits.GPM, HydParam.Demand, 2)

    def test_prepare_arc_data_tracks_static_length_and_diameter(self):
        results = SimpleNamespace(
            link={
                "flowrate": pd.DataFrame([[-0.01, 0.02], [0.03, -0.04]], index=[0, 3600], columns=["P1", "P2"]),
                "velocity": pd.DataFrame([[1.0, 2.0], [3.0, 4.0]], index=[0, 3600], columns=["P1", "P2"]),
                "headloss": pd.DataFrame([[0.1, 0.2], [0.3, 0.4]], index=[0, 3600], columns=["P1", "P2"]),
                "setting": pd.DataFrame([[1.0, 1.0], [1.0, 1.0]], index=[0, 3600], columns=["P1", "P2"]),
                "reaction_rate": pd.DataFrame([[0.0, 0.0], [0.0, 0.0]], index=[0, 3600], columns=["P1", "P2"]),
                "friction_factor": pd.DataFrame([[0.01, 0.02], [0.03, 0.04]], index=[0, 3600], columns=["P1", "P2"]),
                "status": pd.DataFrame([[1, 0], [2, 1]], index=[0, 3600], columns=["P1", "P2"]),
            }
        )
        prepared = _prepare_arc_data(results, _build_mock_inp_handler(), round_decimals=2)

        assert prepared.arc_ids == ["P1", "P2"]
        assert prepared.length["P1"] == _convert_from_si(1000.0, FlowUnits.GPM, HydParam.Length, 2)
        assert prepared.diameter["P2"] == _convert_from_si(0.2, FlowUnits.GPM, HydParam.PipeDiameter, 2)
        assert prepared.flow.loc[0, "P1"] < 0


class TestArcDirectionTracking:
    def test_negative_first_timestep_flow_is_detected(self):
        prepared = _PreparedArcData(
            arc_ids=["P1", "P2", "P3"],
            time_strings=["0:00:00", "1:00:00"],
            length={"P1": 100.0, "P2": 100.0, "P3": 100.0},
            diameter={"P1": 0.3, "P2": 0.3, "P3": 0.3},
            flow=pd.DataFrame([[-1.0, 2.0, 3.0], [-4.0, -5.0, 6.0]], index=[0, 3600], columns=["P1", "P2", "P3"]),
            velocity=None,
            headloss=None,
            setting=None,
            reaction=None,
            ffactor=None,
            status=None,
        )

        reversed_arcs = set()
        for t_idx, _time_str in enumerate(prepared.time_strings):
            for a_idx, arc_id in enumerate(prepared.arc_ids):
                flow = prepared.flow.iat[t_idx, a_idx]
                if t_idx == 0 and flow < 0:
                    reversed_arcs.add(arc_id)

        assert reversed_arcs == {"P1"}


@pytest.mark.skipif(not hasattr(wntr.network, "WaterNetworkModel"), reason="WNTR not available")
class TestPrepareDataWithWntrNetwork:
    def test_prepare_data_with_net1(self):
        try:
            wn = wntr.network.WaterNetworkModel("Net1.inp")
        except Exception:
            pytest.skip("Net1.inp example network not available")

        sim = wntr.sim.EpanetSimulator(wn)
        results = sim.run_sim()
        inp_handler = SimpleNamespace(file_object=wn)

        prepared_nodes = _prepare_node_data(results, inp_handler, round_decimals=2)
        prepared_arcs = _prepare_arc_data(results, inp_handler, round_decimals=2)

        assert len(prepared_nodes.node_ids) > 0
        assert len(prepared_arcs.arc_ids) > 0
        assert len(prepared_nodes.time_strings) == len(prepared_nodes.demand.index)
        assert len(prepared_arcs.time_strings) == len(prepared_arcs.flow.index)
        assert prepared_arcs.length
