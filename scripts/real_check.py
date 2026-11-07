"""Trace a folder of real masks: timing, what was found, and how steady the
trace stays when the mask is damaged.

    python scripts/real_check.py data/ozgenel/BW -o real-check -j 8

Real masks label pixels, not centrelines, so there is no true line to score
against. Instead each mask is traced as given, then damaged the way a weaker
segmentation model would leave it (ragged edges, breaks, pinholes, specks)
and traced again; the second trace is scored against the first.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor

import cv2
import numpy as np

from fine_tracing import trace
from fine_tracing.geometry import resample
from fine_tracing.metrics import evaluate, lines_from_dict
from fine_tracing.synth import damage


def one(job):
    path, seed = job
    mask = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    t0 = time.perf_counter()
    res = trace(mask)
    ms = (time.perf_counter() - t0) * 1000
    row = dict(
        image=os.path.basename(path),
        height=mask.shape[0],
        width=mask.shape[1],
        ms=round(ms, 1),
        cracks=len(res.cracks),
        length_px=round(res.length, 1),
        max_width_px=round(res.max_width, 2) if np.isfinite(res.max_width) else None,
        branches=sum(len(c.paths) - 1 for c in res.cracks),
        bridges=sum(c.gaps for c in res.cracks),
        corner_fallback=sum(1 for c in res.cracks if "corners" in c.method),
    )
    if not res.cracks:
        return row
    paths = []
    for c in res.cracks:
        for p in c.paths:
            if len(p.points) < 2:
                continue
            q, _ = resample(p.points, 0.5)
            w = np.interp(np.linspace(0, 1, len(q)), np.linspace(0, 1, len(p.points)), p.width_filled())
            paths.append((q, np.maximum(w, 1.0)))
    rng = np.random.default_rng(seed)
    spoilt, _ = damage(res.mask, paths, rng, ragged=0.3, gaps=2, holes=True, specks=12)
    res2 = trace(spoilt)
    sc = evaluate(lines_from_dict(res2.to_dict()), lines_from_dict(res.to_dict()), tol=3.0)
    row.update({f"damaged_{k}": round(v, 4) for k, v in sc.items() if k in ("f1", "mean_dist", "length_error")})
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("masks")
    ap.add_argument("-o", "--output", default="real-check")
    ap.add_argument("-j", "--workers", type=int, default=4)
    a = ap.parse_args()
    files = sorted(
        os.path.join(a.masks, f) for f in os.listdir(a.masks) if f.lower().endswith((".png", ".jpg", ".bmp"))
    )
    os.makedirs(a.output, exist_ok=True)
    jobs = [(f, 1000 + i) for i, f in enumerate(files)]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        rows = list(ex.map(one, jobs))
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(os.path.join(a.output, "real.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    def col(k):
        v = np.array([r[k] for r in rows if r.get(k) is not None], float)
        return v[np.isfinite(v)]

    summary = dict(
        images=len(rows),
        image_size=f"{rows[0]['width']} x {rows[0]['height']}" if rows else None,
        median_ms=float(np.median(col("ms"))),
        p95_ms=float(np.percentile(col("ms"), 95)),
        cracks=int(col("cracks").sum()),
        images_with_branches=int((col("branches") > 0).sum()),
        bridges=int(col("bridges").sum()),
        corner_fallbacks=int(col("corner_fallback").sum()),
        damaged_f1_mean=float(col("damaged_f1").mean()),
        damaged_mean_dist_median=float(np.median(col("damaged_mean_dist"))),
        damaged_abs_length_error_median=float(np.median(np.abs(col("damaged_length_error")))),
    )
    with open(os.path.join(a.output, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
