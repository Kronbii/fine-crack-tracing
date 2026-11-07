"""Trace the two example walls and print what was measured.

    python examples/quickstart.py

Writes an overlay for each wall to results/quickstart/.
"""

from pathlib import Path

import cv2

from fine_tracing import trace
from fine_tracing.render import overlay

HERE = Path(__file__).parent
OUT = Path("results/quickstart")
OUT.mkdir(parents=True, exist_ok=True)

for mask_path in sorted((HERE / "masks").glob("*.png")):
    name = mask_path.stem
    mask = cv2.imread(str(mask_path), cv2.IMREAD_UNCHANGED)
    photo = cv2.imread(str(HERE / "photos" / f"{name}.jpg"))
    result = trace(mask, photo)

    print(f"{name}: {len(result.cracks)} crack(s), {result.length:.0f} px of crack")
    for crack in result.cracks:
        w = crack.width_stats()
        print(
            f"  #{crack.id} {crack.pattern:<8} {crack.length:7.0f} px long, "
            f"{len(crack.paths) - 1:2d} branch(es), width {w['median']:.1f} px median, {w['max']:.1f} px max"
        )

    cv2.imwrite(str(OUT / f"{name}.jpg"), overlay(result, photo))

print(f"overlays in {OUT}/")
