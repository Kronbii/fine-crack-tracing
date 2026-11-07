"""Rebuild the figures in docs/media.

    python scripts/make_figures.py --bench bench/ [--real data/ozgenel --pick 001,011]

``--bench`` is a folder written by ``fine-tracing bench``. ``--real`` is a
folder with ``BW/`` masks and ``rgb/`` photos from the Concrete Crack
Segmentation Dataset (Özgenel 2019, CC BY 4.0); without it the real-photo
figures are skipped.
"""

from __future__ import annotations

import argparse
import csv
import os
from dataclasses import replace

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from skimage.morphology import skeletonize  # noqa: E402

from fine_tracing import graph as G  # noqa: E402
from fine_tracing import legacy, trace  # noqa: E402
from fine_tracing.mask import binarize, clean  # noqa: E402
from fine_tracing.render import overlay  # noqa: E402
from fine_tracing.synth import PRESETS, make_sample  # noqa: E402

BG = "#0c0d0e"
FG = "#e8e8e6"
DIM = "#8a8f94"
MASK = (78, 66, 74)
OLD = "#c5a3ff"
TRACERS_SHOWN = ["v0.1 ORB, y-order", "v0.1 Shi-Tomasi + MST", "plain skeleton", "v1 auto"]
COLORS = {
    "v0.1 ORB, y-order": "#6b7075",
    "v0.1 Shi-Tomasi + MST": "#c5a3ff",
    "plain skeleton": "#7fb3d5",
    "v1 corners": "#f2d14b",
    "v1 auto": "#5ee0a0",
}


def _style():
    plt.rcParams.update(
        {
            "figure.facecolor": BG,
            "axes.facecolor": BG,
            "savefig.facecolor": BG,
            "text.color": FG,
            "axes.labelcolor": FG,
            "xtick.color": DIM,
            "ytick.color": DIM,
            "axes.edgecolor": "#3a3d40",
            "font.family": "DejaVu Sans",
            "font.size": 10,
        }
    )


def _rgb(bgr):
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def _mask_canvas(mask):
    img = np.full(mask.shape + (3,), (16, 15, 13), np.uint8)
    img[mask] = MASK
    return img


def _poly(img, pts, color, th=2):
    if len(pts) >= 2:
        p = np.round(np.asarray(pts) * 4).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [p], False, color, th, cv2.LINE_AA, shift=2)


# ---------------------------------------------------------------------------
# before / after on the repository's test mask
# ---------------------------------------------------------------------------


def before_after(mask_path, out):
    raw = cv2.imread(mask_path, cv2.IMREAD_UNCHANGED)
    m = binarize(raw)
    m8 = m.astype(np.uint8) * 255
    frame = cv2.cvtColor(m8, cv2.COLOR_GRAY2BGR)
    old = legacy.trace(m8, frame, "shitomasi", "MST")
    res = trace(raw)

    left = _mask_canvas(m)
    lw = 5
    old_bgr = tuple(int(OLD[i : i + 2], 16) for i in (5, 3, 1))
    for p in old:
        _poly(left, p, old_bgr, lw)
        for q in p:
            cv2.circle(left, tuple(np.round(q).astype(int)), 6, old_bgr, -1, cv2.LINE_AA)
    right = overlay(res, None, labels=False, legend=False, line=lw)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.9))
    old_lens = [float(np.linalg.norm(np.diff(p, axis=0), axis=1).sum()) if len(p) > 1 else 0.0 for p in old]
    for ax, img, title in (
        (axes[0], left, "v0.1: Shi-Tomasi corners + MST path"),
        (axes[1], right, "v1: skeleton graph, width along the crack"),
    ):
        ax.imshow(_rgb(img))
        ax.set_title(title, color=FG, fontsize=12, loc="left")
        ax.axis("off")
    # lengths beside each crack
    for p, L in zip(old, old_lens):
        if len(p):
            x, y = p[len(p) // 2]
            axes[0].text(x + 120, y, f"{L:.0f} px", color=OLD, fontsize=10)
    for c in res.cracks:
        x, y = c.trunk.points[len(c.trunk.points) // 2]
        ws = c.width_stats()
        axes[1].text(
            x + 120,
            y,
            f"{c.length:.0f} px\nwidth {ws['median']:.0f}–{ws['max']:.0f} px\n"
            f"{len(c.paths) - 1} branch{'es' if len(c.paths) != 2 else ''}",
            color=FG,
            fontsize=10,
        )
    fig.text(
        0.01,
        0.02,
        "Input: test-frames/test.png, a crack mask (2448 x 2048 px) used as its own frame. "
        "Dashed white: a break in the mask, bridged. Rings: junctions. Colour: width, mint (thin) to magenta (wide).",
        color=DIM,
        fontsize=8.5,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(out, dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------------------
# what each stage does
# ---------------------------------------------------------------------------


def stages(mask, out, crop=None, photo=None):
    if crop is not None:
        y0, y1, x0, x1 = crop
        mask = mask[y0:y1, x0:x1]
        photo = photo[y0:y1, x0:x1] if photo is not None else None
    m, _ = clean(binarize(mask))
    sk = skeletonize(m)
    g = G.from_skeleton(sk)
    res = trace(mask, photo)

    H, W = m.shape
    lw = max(3, int(round(max(H, W) / 140)))
    a = _mask_canvas(m)
    from scipy.spatial import cKDTree

    b = _mask_canvas(m)
    fin = np.vstack([p.points for cr in res.cracks for p in cr.paths]) if res.cracks else np.zeros((1, 2))
    tree = cKDTree(fin)
    for e in g.edges.values():
        d, _ = tree.query(e.pts)
        spur = float(np.mean(d > 4.0)) > 0.5
        _poly(b, e.pts, (80, 80, 255) if spur else (255, 255, 255), max(2, lw - 1))
    for n in g.nodes:
        d = g.degree(n)
        col = (90, 90, 255) if d >= 3 else (255, 200, 120)
        cv2.circle(b, tuple(np.round(g.nodes[n]).astype(int)), 3 * lw, col, max(1, lw // 2), cv2.LINE_AA)
    c = _mask_canvas(m)
    palette = [(160, 224, 94), (75, 209, 242), (154, 61, 255), (230, 180, 90), (120, 120, 255)]
    for cr in res.cracks:
        for k, p in enumerate(cr.paths):
            col = palette[min(k, len(palette) - 1)] if k else (240, 240, 240)
            pts = p.points
            for i in range(len(pts) - 1):
                if not p.bridged[i]:
                    _poly(c, pts[i : i + 2], col, lw)
            j = 0
            while j < len(p.bridged):
                if p.bridged[j]:
                    k2 = j
                    while k2 < len(p.bridged) and p.bridged[k2]:
                        k2 += 1
                    _poly(c, [pts[j], pts[k2]], (60, 230, 255), lw)
                    j = k2
                else:
                    j += 1
        for jn in cr.junctions:
            cv2.circle(c, tuple(np.round(jn).astype(int)), 4 * lw, (255, 255, 255), max(1, lw // 2), cv2.LINE_AA)
    d = overlay(res, photo, labels=False, legend=False, line=lw)

    nj = sum(1 for n in g.nodes if g.degree(n) >= 3)
    ne = sum(1 for n in g.nodes if g.degree(n) == 1)
    titles = [
        "1  The mask",
        f"2  Its skeleton\n{nj} junctions, {ne} ends",
        f"3  Spurs cut, breaks bridged\n{sum(len(cr.junctions) for cr in res.cracks)} junctions, "
        f"{sum(len(cr.paths) - 1 for cr in res.cracks)} branches",
        "4  Smoothed, centred,\nwidth at every point",
    ]
    fig, axes = plt.subplots(1, 4, figsize=(16, 4.0 * H / W + 1.0))
    for ax, img, t in zip(axes, (a, b, c, d), titles):
        ax.imshow(_rgb(img))
        ax.set_title(t, color=FG, fontsize=11, loc="left")
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out, dpi=100)
    plt.close(fig)


# ---------------------------------------------------------------------------
# benchmark charts
# ---------------------------------------------------------------------------


def bench_charts(bench_dir, out_presets, out_sweep):
    rows = list(csv.DictReader(open(os.path.join(bench_dir, "summary.csv"))))
    presets = [p for p in ("clean", "ragged", "broken", "realistic")]

    def val(p, t, k):
        for r in rows:
            if r["preset"] == p and r["tracer"] == t:
                return float(r[k])
        return float("nan")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
    x = np.arange(len(presets))
    wbar = 0.8 / len(TRACERS_SHOWN)
    for k, t in enumerate(TRACERS_SHOWN):
        f1 = [val(p, t, "f1") for p in presets]
        le = [val(p, t, "abs_length_error") * 100 for p in presets]
        xs = x + k * wbar - 0.4 + wbar / 2
        axes[0].bar(xs, f1, wbar * 0.92, label=t, color=COLORS[t])
        axes[1].bar(xs, le, wbar * 0.92, label=t, color=COLORS[t])
    axes[0].set_ylim(0, 1.05)
    axes[0].set_title("Centreline F1 within 3 px  (higher is better)", loc="left", color=FG)
    axes[1].set_title("Length error, mean absolute %  (lower is better, log scale)", loc="left", color=FG)
    axes[1].set_yscale("log")
    axes[1].set_ylim(0.1, 150)
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(["clean masks", "ragged edges", "broken", "realistic\n(ragged, broken, specks)"])
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(axis="x", colors=FG)
    leg = axes[0].legend(fontsize=9, frameon=False, loc="upper left", bbox_to_anchor=(0, -0.16), ncol=4)
    for t in leg.get_texts():
        t.set_color(FG)
    fig.tight_layout()
    fig.savefig(out_presets, dpi=120)
    plt.close(fig)

    srows = list(csv.DictReader(open(os.path.join(bench_dir, "width_sweep.csv"))))
    widths = sorted({float(r["sweep_width"]) for r in srows})

    def mean(t, w, k):
        v = [
            float(r[k])
            for r in srows
            if r["tracer"] == t and float(r["sweep_width"]) == w and r.get(k) not in ("", None)
        ]
        v = [a for a in v if np.isfinite(a)]
        return float(np.mean(v)) if v else float("nan")

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2))
    for t in TRACERS_SHOWN:
        axes[0].plot(widths, [mean(t, w, "mean_dist") for w in widths], "o-", color=COLORS[t], label=t, lw=2, ms=4)
        axes[1].plot(
            widths, [mean(t, w, "abs_length_error") * 100 for w in widths], "o-", color=COLORS[t], label=t, lw=2, ms=4
        )
    axes[0].set_title("Distance from the true centreline, px", loc="left", color=FG)
    axes[1].set_title("Length error, mean absolute %", loc="left", color=FG)
    for ax in axes:
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xticks(widths)
        ax.set_xticklabels([f"{w:g}" for w in widths])
        ax.set_xlabel("crack width, px")
        ax.spines[["top", "right"]].set_visible(False)
    leg = axes[0].legend(fontsize=9, frameon=False)
    for t in leg.get_texts():
        t.set_color(FG)
    fig.tight_layout()
    fig.savefig(out_sweep, dpi=120)
    plt.close(fig)


def synth_example(out, seed=21):
    s = make_sample(np.random.default_rng(seed), replace(PRESETS["realistic"], size=768))
    res = trace(s["mask"], s["photo"])
    gt = s["gt"]
    a = s["photo"].copy()
    b = _mask_canvas(s["mask"])
    for c in gt["cracks"]:
        for p in c["paths"]:
            _poly(b, p["points"], (94, 224, 160), 2)
    c_img = overlay(res, s["photo"], labels=False, legend=False, line=2)
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.3))
    for ax, img, t in zip(
        axes,
        (a, b, c_img),
        ("Generated photo", "Damaged mask, with the true centreline", "Traced: width along each crack"),
    ):
        ax.imshow(_rgb(img))
        ax.set_title(t, loc="left", color=FG, fontsize=11)
        ax.axis("off")
    fig.tight_layout()
    fig.savefig(out, dpi=100, pil_kwargs={"quality": 85})
    plt.close(fig)


# ---------------------------------------------------------------------------
# real photos
# ---------------------------------------------------------------------------


def _load_real(real_dir, name):
    mask = cv2.imread(os.path.join(real_dir, "BW", name + ".jpg"), cv2.IMREAD_GRAYSCALE)
    photo = cv2.imread(os.path.join(real_dir, "rgb", name + ".jpg"))
    return mask, photo


def hero(real_dir, name, crop, out, width=1600):
    mask, photo = _load_real(real_dir, name)
    res = trace(mask, photo)
    img = overlay(res, photo, labels=False)
    y0, y1, x0, x1 = crop
    img = img[y0:y1, x0:x1]
    s = width / img.shape[1]
    img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return res


def gallery(real_dir, names, out, height=900):
    tiles = []
    for n in names:
        mask, photo = _load_real(real_dir, n)
        res = trace(mask, photo)
        img = overlay(res, photo, labels=False, legend=False, line=max(6, int(round(max(mask.shape) / 230))))
        s = height / img.shape[0]
        tiles.append(cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA))
        tiles.append(np.full((height, 12, 3), 12, np.uint8))
    img = np.hstack(tiles[:-1])
    if img.shape[1] > 2400:
        s = 2400 / img.shape[1]
        img = cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    cv2.imwrite(out, img, [cv2.IMWRITE_JPEG_QUALITY, 84])


def _ints(v):
    return tuple(int(x) for x in v.split(","))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--out", default="docs/media")
    ap.add_argument("--test-mask", default="test-frames/test.png")
    ap.add_argument("--real", help="folder with BW/ masks and rgb/ photos")
    ap.add_argument("--hero", default="609")
    ap.add_argument("--hero-crop", default="2000,4032,0,3024", help="y0,y1,x0,x1")
    ap.add_argument("--stages", default="609")
    ap.add_argument("--stages-crop", default="1750,2750,950,1950", help="y0,y1,x0,x1")
    ap.add_argument("--gallery", default="120,607,284")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    _style()
    before_after(a.test_mask, os.path.join(a.out, "before-after.png"))
    bench_charts(a.bench, os.path.join(a.out, "benchmark.png"), os.path.join(a.out, "width-sweep.png"))
    synth_example(os.path.join(a.out, "synthetic.jpg"))
    if a.real:
        hero(a.real, a.hero, _ints(a.hero_crop), os.path.join(a.out, "hero.jpg"))
        mask, photo = _load_real(a.real, a.stages)
        stages(mask, os.path.join(a.out, "stages.png"), crop=_ints(a.stages_crop), photo=photo)
        gallery(a.real, [n for n in a.gallery.split(",") if n], os.path.join(a.out, "real-gallery.jpg"))
    else:
        raw = cv2.imread(a.test_mask, cv2.IMREAD_UNCHANGED)
        stages(raw, os.path.join(a.out, "stages.png"), crop=(1150, 2048, 80, 980))


if __name__ == "__main__":
    main()
