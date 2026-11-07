import cv2
import numpy as np
import pytest

from fine_tracing import TraceConfig, trace
from fine_tracing.mask import binarize, to_float


def band(shape=(200, 400), p0=(30, 100), p1=(370, 100), width=9):
    """A straight crack. OpenCV draws thickness t as t + 2 rows, so build it
    from rows instead: exactly ``width`` rows, x from p0 to p1."""
    m = np.zeros(shape, np.uint8)
    if p0[1] == p1[1]:
        y0 = p0[1] - width // 2
        m[y0 : y0 + width, p0[0] : p1[0] + 1] = 255
    else:
        cv2.line(m, p0, p1, 255, width)
    return m


def test_straight_crack_length_and_width():
    m = band(width=9)
    r = trace(m)
    assert len(r.cracks) == 1
    c = r.cracks[0]
    # the band runs from x=30 to x=370, so 341 px edge to edge
    assert abs(c.length - 341) < 2
    ws = c.width_stats()
    assert abs(ws["median"] - 9) < 0.6
    assert c.direction == "horizontal"
    assert len(c.paths) == 1


def test_diagonal_length_is_not_staircase():
    m = np.zeros((400, 400), np.uint8)
    cv2.line(m, (40, 40), (360, 280), 255, 5)
    true_len = np.hypot(320, 240)
    r = trace(m, extend_ends=False)
    raw = trace(m, smoothing=0, extend_ends=False, recentre=False)
    assert abs(r.cracks[0].length - true_len) / true_len < 0.03
    # the pixel staircase overstates a diagonal; smoothing removes that
    assert raw.cracks[0].length > r.cracks[0].length


def test_branch_is_found_and_spurs_are_cut():
    m = np.zeros((300, 300), np.uint8)
    cv2.line(m, (20, 150), (280, 150), 255, 11)
    cv2.line(m, (150, 150), (230, 40), 255, 7)
    # a bump on the edge that would leave a spur
    cv2.circle(m, (80, 157), 5, 255, -1)
    r = trace(m)
    assert len(r.cracks) == 1
    c = r.cracks[0]
    assert len(c.paths) == 2, [p.length for p in c.paths]
    assert len(c.junctions) == 1
    assert np.linalg.norm(c.junctions[0] - [150, 150]) < 8
    assert c.pattern == "branched"


def test_gap_is_bridged_and_reported():
    m = band(width=7)
    m[:, 190:210] = 0  # a 20 px break
    joined = trace(m)
    split = trace(m, bridge=False)
    assert len(joined.cracks) == 1
    assert len(split.cracks) == 2
    assert 15 <= joined.cracks[0].gap_length <= 25
    assert len(joined.bridges) == 1


def test_bridge_refuses_a_sideways_gap():
    m = np.zeros((300, 300), np.uint8)
    cv2.line(m, (20, 100), (140, 100), 255, 5)
    cv2.line(m, (160, 200), (280, 200), 255, 5)  # parallel, offset 100 px
    r = trace(m)
    assert len(r.cracks) == 2


def test_px_size_and_classes():
    m = band(width=9)
    r = trace(m, px_size=0.1, width_classes=(0.5, 1.0))
    row = r.rows()[0]
    assert abs(row["length_mm"] - row["length_px"] * 0.1) < 1e-3
    assert abs(row["median_width_mm"] - 0.9) < 0.08
    total = row["length_w<0.5mm"] + row["length_w0.5-1mm"] + row["length_w>=1mm"]
    assert total > 0.8 * row["length_mm"]


@pytest.mark.parametrize("method", ["skeleton", "corners", "auto"])
def test_methods_follow_the_centre_of_a_wide_crack(method):
    m = band(width=25)
    r = trace(m, method=method)
    pts = r.cracks[0].trunk.points
    inner = pts[(pts[:, 0] > 60) & (pts[:, 0] < 340)]
    assert np.abs(inner[:, 1] - 100).max() < 2.5


def test_mask_formats():
    gray = band()
    red = np.zeros(gray.shape + (3,), np.uint8)
    red[..., 2] = gray
    rgba = np.zeros(gray.shape + (4,), np.uint8)
    rgba[..., 3] = gray
    prob = gray.astype(np.float32) / 255 * 0.8
    for m in (gray, red, rgba, gray > 0):
        assert binarize(m).sum() == (gray > 0).sum()
    assert binarize(prob, threshold=0.5).sum() == (gray > 0).sum()
    assert to_float(np.zeros((4, 4), np.uint16)).max() == 0


def test_hysteresis_keeps_weak_pixels_touching_strong_ones():
    p = np.zeros((50, 50), np.float32)
    p[10:40, 24:27] = 0.4
    p[20:22, 24:27] = 0.9
    p[5:8, 5:8] = 0.4  # weak and alone
    b = binarize(p, hysteresis=(0.3, 0.6))
    assert b[10:40, 24:27].all() and not b[5:8, 5:8].any()


def test_empty_mask():
    r = trace(np.zeros((64, 64), np.uint8))
    assert r.cracks == [] and r.length == 0


def test_exports_are_consistent():
    m = band(width=9)
    r = trace(m)
    d = r.to_dict()
    assert d["summary"]["cracks"] == 1
    path = d["cracks"][0]["paths"][0]
    assert len(path["points"]) == len(path["width_px"]) == len(path["bridged"]) + 1
    gj = r.to_geojson()
    assert gj["features"][0]["geometry"]["type"] == "LineString"
    assert r.to_svg().startswith("<svg")


def test_config_round_trip():
    cfg = TraceConfig(px_size=0.2, width_classes=(0.1, 0.3), hysteresis=(0.2, 0.5))
    assert TraceConfig.from_dict(cfg.to_dict()) == cfg
    with pytest.raises(ValueError):
        TraceConfig(method="nope")
    with pytest.raises(ValueError):
        TraceConfig.from_dict({"bogus": 1})
