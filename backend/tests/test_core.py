import pytest
from app.gis import risk
from app.services import agri


def test_classification():
    assert risk.classify(500, "ec_us_cm") == "Low" and risk.classify(6000, "ec_us_cm") == "High"


def test_sar_formula():
    assert risk.sar(230, 40, 24) == pytest.approx(6.0, abs=0.7)


def test_risk_confidence_drops_with_missing_inputs():
    full = risk.compute_risk(2, 4000, 700, 8, 12, 3, -20, 0.9)
    part = risk.compute_risk(distance_km=2, ec=4000)
    assert part["confidence"] < full["confidence"] and "not confirmed" in part["label"]


def test_unverified_lowers_confidence():
    assert risk.compute_risk(ec=3000, verified=False)["confidence"] < risk.compute_risk(ec=3000)["confidence"]


def test_blending():
    assert agri.blending(5000, 500, 2000)["fresh_fraction"] == pytest.approx(0.67, abs=.01)
    assert agri.blending(500, 500, 400) is None


def test_anomaly():
    assert risk.detect_anomaly([1000, 1010, 990, 1005, 3000])["anomalous"]
