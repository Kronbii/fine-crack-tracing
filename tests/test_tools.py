import json

import cv2
import numpy as np

from fine_tracing import legacy, trace
from fine_tracing.cli import main
from fine_tracing.graph import from_skeleton
from fine_tracing.metrics import centreline_scores, evaluate, lines_from_dict, point_scores
from fine_tracing.synth import PRESETS, make_sample


def test_skeleton_graph_y_shape():
    sk = np.zeros((40, 40), bool)
    sk[20, 5:20] = True
    for k in range(15):
        sk[20 - k, 20 + k] = True
        sk[20 + k, 20 + k] = True
    g = from_skeleton(sk)
    degs = sorted(g.degree(n) for n in g.nodes)
    assert degs == [1, 1, 1, 3]
    assert len(g.edges) == 3


def test_staircase_is_not_a_junction():
    sk = np.zeros((20, 20), bool)
    for k in range(10):
        sk[k + 2, k + 2] = True
        sk[k + 2, k + 3] = True  # 4-connected staircase
    g = from_skeleton(sk)
    assert all(g.degree(n) <= 2 for n in g.nodes)


def test_scores():
    line = np.column_stack([np.arange(100.0), np.full(100, 10.0)])
    s = centreline_scores(line, line, 3)
    assert s["f1"] == 1.0 and s["mean_dist"] == 0
    shifted = line + [0, 5]
    assert centreline_scores(shifted, line, 3)["f1"] == 0
    assert point_scores([[0, 0], [10, 10]], [[1, 1]], 3) == {"precision": 0.5, "recall": 1.0}


def test_synthetic_sample_traces_well():
    rng = np.random.default_rng(3)
    s = make_sample(rng, PRESETS["clean"])
    gt = lines_from_dict(s["gt"])
    r = trace(s["mask"], s["photo"])
    sc = evaluate(lines_from_dict(r.to_dict()), gt)
    assert sc["f1"] > 0.9
    assert abs(sc["length_error"]) < 0.05


def test_legacy_runs():
    m = np.zeros((200, 200), np.uint8)
    cv2.line(m, (20, 30), (180, 170), 255, 9)
    photo = cv2.cvtColor(255 - m // 2, cv2.COLOR_GRAY2BGR)
    for det, srt in (("orb", "classic"), ("shitomasi", "MST"), ("shitomasi", "greedy")):
        polys = legacy.trace(m, photo, det, srt)
        assert len(polys) == 1


def test_cli_trace_and_eval(tmp_path):
    rng = np.random.default_rng(1)
    s = make_sample(rng, PRESETS["broken"])
    (tmp_path / "masks").mkdir()
    (tmp_path / "photos").mkdir()
    (tmp_path / "truth").mkdir()
    cv2.imwrite(str(tmp_path / "masks" / "a.png"), s["mask"].astype(np.uint8) * 255)
    cv2.imwrite(str(tmp_path / "photos" / "a.jpg"), s["photo"])
    (tmp_path / "truth" / "a.json").write_text(json.dumps(s["gt"]))
    out = tmp_path / "out"
    assert (
        main(
            [
                "trace",
                str(tmp_path / "masks"),
                "--photos",
                str(tmp_path / "photos"),
                "-o",
                str(out),
                "-q",
                "--px-size",
                "0.2",
            ]
        )
        == 0
    )
    for f in (
        "json/a.json",
        "geojson/a.geojson",
        "svg/a.svg",
        "overlays/a.jpg",
        "centrelines/a.png",
        "cracks.csv",
        "summary.json",
    ):
        assert (out / f).exists(), f
    assert main(["eval", str(out / "json"), str(tmp_path / "truth"), "-o", str(tmp_path / "scores")]) == 0
    scores = json.loads((tmp_path / "scores" / "scores.json").read_text())
    assert scores["mean"]["f1"] > 0.8
