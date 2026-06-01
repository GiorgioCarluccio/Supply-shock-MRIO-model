"""Non-Databricks tests for the modelling layer.

Validates the label parser, account classification, the SAM-to-model input
builder (on a small synthetic SAM and on the real artifact if present), the
propagation model and the KPI helpers. No Databricks connection is required.

Run from the project root::

    .\\.venv\\Scripts\\python.exe scripts\\test_model_layer.py
"""

from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from climate_risk_io.model import input_builder, kpi, label_parser, results
from climate_risk_io.model.io_model import IOClimateModel
from config.paths import MODEL_INPUTS_DIR

TOL = 1e-9
TEST_TMP_DIR = PROJECT_ROOT / ".test_tmp"
_TEMP_COUNTER = 0


@contextmanager
def temporary_directory():
    global _TEMP_COUNTER
    _TEMP_COUNTER += 1
    TEST_TMP_DIR.mkdir(exist_ok=True)
    path = TEST_TMP_DIR / f"case_{_TEMP_COUNTER}"
    path.mkdir(parents=True, exist_ok=True)
    yield str(path)


# --------------------------------------------------------------------------- #
# Synthetic SAM
# --------------------------------------------------------------------------- #
# Account order (rows == columns == this order).
SYNTH_ACCOUNTS = [
    # productive
    ("IT001", "A01", "A"),
    ("IT001", "C10", "I"),
    ("IT002", "A01", "A"),
    ("IT002", "C10", "I"),
    # value added
    ("EU-ITA", "LAB", "L"),
    ("EU-ITA", "CAP", "K"),
    ("EU-ITA", "TAX", "T"),
    # final demand
    ("EU-ITA", "HH", "HH"),
    ("EU-ITA", "CF", "CF"),
    ("EU-ITA", "GOV", "G"),
    ("EU-ITA", "ROW", "R"),
]
PROD = [0, 1, 2, 3]
VA = [4, 5, 6]
FD = [7, 8, 9, 10]


def make_synthetic_sam(tmp_dir: Path) -> Path:
    """Write a small synthetic dense SAM artifact and return its directory."""
    n = len(SYNTH_ACCOUNTS)
    Z = np.zeros((n, n), dtype=float)

    rng = np.random.default_rng(42)
    # Productive -> productive intermediate flows.
    for i in PROD:
        for j in PROD:
            Z[i, j] = float(rng.integers(1, 10))
    # Productive -> final demand.
    for i in PROD:
        for j in FD:
            Z[i, j] = float(rng.integers(5, 20))
    # Value added -> productive (VA rows, productive columns).
    for i in VA:
        for j in PROD:
            Z[i, j] = float(rng.integers(2, 8))

    x = Z.sum(axis=1)

    nodes = pd.DataFrame(
        {
            "node_id": np.arange(n, dtype=np.int64),
            "region_code": [a[0] for a in SYNTH_ACCOUNTS],
            "sector_code": [a[1] for a in SYNTH_ACCOUNTS],
            "macrosector_code": [a[2] for a in SYNTH_ACCOUNTS],
            "node_label": [f"{a[0]}__{a[1]}__{a[2]}" for a in SYNTH_ACCOUNTS],
        }
    )

    tmp_dir.mkdir(parents=True, exist_ok=True)
    nodes.to_csv(tmp_dir / "nodes.csv", index=False)
    np.save(tmp_dir / "z_matrix.npy", Z)
    np.save(tmp_dir / "x_vector.npy", x)
    return tmp_dir


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #
def test_label_parser() -> None:
    parsed = label_parser.parse_account_label("ITC11__C10-12__I")
    assert parsed == {
        "region_code": "ITC11",
        "sector_code": "C10-12",
        "macrosector_code": "I",
    }, parsed

    for bad in ["ITC11__C10", "ITC11", "A__B__C__D", "ITC11____I"]:
        try:
            label_parser.parse_account_label(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected ValueError for malformed label {bad!r}")


def test_classification() -> None:
    cases = {
        "A": "productive",
        "I": "productive",
        "S": "productive",
        "HH": "final_demand",
        "CF": "final_demand",
        "G": "final_demand",
        "R": "final_demand",
        "L": "value_added",
        "K": "value_added",
        "T": "value_added",
    }
    for macro, expected in cases.items():
        got = label_parser.classify_account({"macrosector_code": macro})
        assert got == expected, f"{macro}: expected {expected}, got {got}"


def test_masks() -> None:
    nodes = pd.DataFrame(
        {
            "node_id": np.arange(len(SYNTH_ACCOUNTS)),
            "region_code": [a[0] for a in SYNTH_ACCOUNTS],
            "sector_code": [a[1] for a in SYNTH_ACCOUNTS],
            "macrosector_code": [a[2] for a in SYNTH_ACCOUNTS],
        }
    )
    meta = input_builder.build_account_metadata(nodes)
    assert int(meta["is_productive_account"].sum()) == 4
    assert int(meta["is_final_demand_account"].sum()) == 4
    assert int(meta["is_value_added_account"].sum()) == 3
    assert int(meta["is_external_input_account"].sum()) == 1
    assert int(meta["is_institutional_account"].sum()) == 7


def test_build_inputs_synthetic() -> None:
    with temporary_directory() as tmp:
        tmp = Path(tmp)
        sam_dir = make_synthetic_sam(tmp / "sam")
        out_dir = tmp / "model_inputs"
        built = input_builder.build_model_inputs(sam_dir, out_dir, write=True)

        Z0 = built["Z0"]
        FD0 = built["FD0"]
        X0 = built["X0"]
        VA0 = built["VA0"]
        IMP0 = built["IMP0"]
        globsec_of = built["globsec_of"]
        nodes = built["productive_nodes"]

        # Dimensions.
        assert Z0.shape == (4, 4), Z0.shape
        assert FD0.shape == (4,), FD0.shape
        assert VA0.shape == (3, 4), VA0.shape
        assert IMP0.shape == (1, 4), IMP0.shape
        assert X0.shape == (4,), X0.shape
        assert globsec_of.shape == (4,), globsec_of.shape
        assert len(nodes) == 4

        # X0 = row_sum(Z0) + FD0.
        assert np.allclose(X0, Z0.sum(axis=1) + FD0, atol=TOL)

        # Two sector groups (A01, C10), each shared across the two regions.
        assert len(np.unique(globsec_of)) == 2
        assert built["sector_mapping"].shape[0] == 2

        # All output files exist.
        for name in [
            "productive_nodes.csv",
            "account_nodes.csv",
            "Z0.npy",
            "FD0.npy",
            "X0.npy",
            "VA0.npy",
            "IMP0.npy",
            "globsec_of.npy",
            "sector_mapping.csv",
            "model_input_report.json",
        ]:
            assert (out_dir / name).exists(), f"missing {name}"


def test_model_runs_synthetic() -> None:
    with temporary_directory() as tmp:
        tmp = Path(tmp)
        sam_dir = make_synthetic_sam(tmp / "sam")
        built = input_builder.build_model_inputs(sam_dir, tmp / "mi", write=False)

        n = len(built["productive_nodes"])
        model = IOClimateModel(
            Z0=built["Z0"],
            FD0=built["FD0"],
            X0=built["X0"],
            sector_group_of=built["globsec_of"],
            node_labels=built["productive_nodes"]["node_label"].tolist(),
        )
        sp = np.zeros(n)
        sp[0] = 0.5
        sd = np.zeros(n)
        run = model.run(sd=sd, sp=sp, gamma=0.5)

        assert "Z_final" in run
        assert run["X_supply_final"].shape == (n,)
        # No shock => no loss baseline sanity: a positive shock yields some loss.
        res = results.summarize_run(run, built["Z0"], built["X0"], built["productive_nodes"])
        assert res.total_loss.shape == (n,)
        assert res.totals["total_loss"] >= -TOL


def test_no_shock_is_lossless() -> None:
    with temporary_directory() as tmp:
        tmp = Path(tmp)
        sam_dir = make_synthetic_sam(tmp / "sam")
        built = input_builder.build_model_inputs(sam_dir, tmp / "mi", write=False)
        n = len(built["productive_nodes"])
        model = IOClimateModel(
            Z0=built["Z0"],
            FD0=built["FD0"],
            X0=built["X0"],
            sector_group_of=built["globsec_of"],
        )
        run = model.run(sd=np.zeros(n), sp=np.zeros(n), gamma=0.5)
        # With no supply shock, feasible output should match baseline output.
        assert np.allclose(run["X_supply_final"], built["X0"], rtol=1e-6, atol=1e-6)


def test_kpi_columns() -> None:
    with temporary_directory() as tmp:
        tmp = Path(tmp)
        sam_dir = make_synthetic_sam(tmp / "sam")
        built = input_builder.build_model_inputs(sam_dir, tmp / "mi", write=False)
        n = len(built["productive_nodes"])
        model = IOClimateModel(
            Z0=built["Z0"],
            FD0=built["FD0"],
            X0=built["X0"],
            sector_group_of=built["globsec_of"],
        )
        sp = np.zeros(n)
        sp[1] = 0.4
        run = model.run(sd=np.zeros(n), sp=sp, gamma=0.5)
        res = results.summarize_run(run, built["Z0"], built["X0"], built["productive_nodes"], top_n=3)

        expected_cols = [
            "origin_node_id",
            "origin_region",
            "origin_sector",
            "destination_node_id",
            "destination_region",
            "destination_sector",
            "delta_value",
            "relative_change",
            "pre_value",
            "post_value",
        ]
        for col in expected_cols:
            assert col in res.top_penalized_flows.columns, f"penalised missing {col}"
            assert col in res.top_favored_flows.columns, f"favoured missing {col}"


def test_real_model_inputs_if_present() -> None:
    """If the real model inputs have been built, validate their consistency."""
    model_dir = MODEL_INPUTS_DIR
    if not (model_dir / "Z0.npy").exists():
        print("SKIP     real model inputs not built; run build_model_inputs_from_sam.py")
        return
    inputs = input_builder.load_model_inputs(model_dir)
    Z0, FD0, X0 = inputs["Z0"], inputs["FD0"], inputs["X0"]
    IMP0 = inputs["IMP0"]
    globsec_of = inputs["globsec_of"]
    n = len(inputs["productive_nodes"])

    assert Z0.shape == (n, n)
    assert FD0.shape == (n,)
    assert X0.shape == (n,)
    assert IMP0.shape[1] == n
    assert globsec_of.shape == (n,)
    assert np.allclose(X0, Z0.sum(axis=1) + FD0, atol=1e-6)


# --------------------------------------------------------------------------- #
# Runner
# --------------------------------------------------------------------------- #
def main() -> int:
    tests = [
        test_label_parser,
        test_classification,
        test_masks,
        test_build_inputs_synthetic,
        test_model_runs_synthetic,
        test_no_shock_is_lossless,
        test_kpi_columns,
        test_real_model_inputs_if_present,
    ]
    print("\n=== Model layer tests ===")
    failed = 0
    for test in tests:
        try:
            test()
            print(f"PASS     {test.__name__}")
        except Exception as exc:  # noqa: BLE001 - report and continue
            failed += 1
            print(f"FAIL     {test.__name__}: {exc!r}")

    print("\n=== Summary ===")
    if failed:
        print(f"{failed} test(s) failed.")
        return 1
    print("All model-layer tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
