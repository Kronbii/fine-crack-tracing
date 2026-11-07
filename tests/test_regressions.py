"""Cases found in review of 1.0, kept so they stay fixed."""

import json

import cv2
import numpy as np
import pytest

from fine_tracing import trace
from fine_tracing.cli import main
from fine_tracing.mask import binarize, to_uint8
from fine_tracing.metrics import load_lines


@pytest.mark.parametrize("dtype", [np.uint8, np.int32, np.int64, np.uint16])
def test_label_masks_of_zeros_and_ones(dtype):
    m = np.zeros((100, 200), dtype)
    m[45:55, 20:180] = 1
    assert binarize(m).sum() == 10 * 160
    assert len(trace(m).cracks) == 1


def test_json_has_no_nan_even_when_widths_are_unmeasurable():
    m = np.ones((600, 900), np.uint8) * 255  # wider than any width probe
    s = trace(m).to_json()

    def refuse(token):
        raise ValueError(token)

    json.loads(s, parse_constant=refuse)


def test_width_against_the_image_border_is_exact():
    for w in (2, 3, 7):
        m = np.zeros((60, 300), np.uint8)
        m[:w, 10:290] = 255
        r = trace(m)
        assert abs(r.cracks[0].width_stats()["median"] - w) < 0.15, w


def test_width_classes_add_up_to_the_traced_length():
    m = np.zeros((300, 400), np.uint8)
    m[145:156, 20:380] = 255
    cv2.line(m, (150, 150), (230, 40), 255, 7)
    cv2.line(m, (250, 150), (330, 260), 255, 7)
    r = trace(m, width_classes=(4.0, 8.0))
    c = r.cracks[0]
    assert len(c.junctions) == 2
    total = sum(c.width_class_lengths([4.0, 8.0]))
    assert abs(total - (c.length - c.gap_length)) < 1.0


def test_bridged_points_have_no_width_at_any_step():
    m = np.zeros((100, 400), np.uint8)
    m[45:52, 30:370] = 255
    m[:, 190:210] = 0
    for step in (1.0, 2.0, 3.0):
        p = trace(m, step=step).cracks[0].trunk
        on_gap = np.zeros(len(p.points), bool)
        on_gap[:-1] |= p.bridged
        on_gap[1:] |= p.bridged
        assert on_gap.any()
        assert np.isnan(p.width[on_gap]).all(), step


def test_eval_measures_image_centrelines_along_the_line(tmp_path):
    img = np.zeros((300, 300), np.uint8)
    cv2.line(img, (25, 25), (275, 275), 255, 1)
    cv2.imwrite(str(tmp_path / "diag.png"), img)
    true = np.hypot(250, 250)
    assert abs(load_lines(str(tmp_path / "diag.png"))["length"] - true) / true < 0.03


@pytest.mark.parametrize(
    "photo",
    [
        np.full((80, 120, 3), 0.6, np.float32),
        np.full((80, 120, 3), 40000, np.uint16),
        np.full((80, 120), 0.6, np.float64),
    ],
)
def test_photos_of_any_depth_keep_their_brightness(photo):
    g = to_uint8(photo)
    assert g.dtype == np.uint8 and 140 <= int(g.mean()) <= 160


def test_v01_spellings_still_work(tmp_path, capsys):
    m = np.zeros((100, 200), np.uint8)
    m[45:55, 20:180] = 255
    (tmp_path / "m").mkdir()
    (tmp_path / "f").mkdir()
    cv2.imwrite(str(tmp_path / "m" / "a.png"), m)
    cv2.imwrite(str(tmp_path / "f" / "a.png"), cv2.cvtColor(255 - m // 2, cv2.COLOR_GRAY2BGR))
    out = tmp_path / "out"
    args = ["-v", "run", "--frames-dir", str(tmp_path / "f"), "--masks-dir", str(tmp_path / "m")]
    assert main(args + ["--output-dir", str(out)]) == 0
    assert (out / "centrelines" / "a.png").exists()
    legacy_metrics = ["metrics", "--ground-truth", str(out / "centrelines"), "--generated", str(out / "centrelines")]
    assert main(legacy_metrics + ["--output-dir", str(tmp_path / "s")]) == 0
    scores = json.loads((tmp_path / "s" / "scores.json").read_text())
    assert scores["mean"]["f1"] == 1.0


def test_help_lists_only_current_commands(capsys):
    with pytest.raises(SystemExit):
        main(["--help"])
    out = capsys.readouterr().out
    assert "SUPPRESS" not in out
    for cmd in ("trace", "eval", "synth", "bench"):
        assert cmd in out
    assert "run" not in out.split("examples:")[0].replace("fine-tracing", "")
