# Changelog

## 1.0.0

A rebuild around the approach the toolkit ended up with in practice: skeletonise the mask, and fall back to Shi-Tomasi corners only where a skeleton cannot describe a crack.

### New

- **Skeleton tracer.** Each crack is thinned to its centreline and turned into a graph of free ends, junctions and the paths between them. Staircase pixels no longer read as junctions.
- **Spur pruning.** Side branches shorter than 2.5 local half-widths are cut, shortest first, so ragged mask edges stop sprouting false branches while real ones stay.
- **Gap bridging.** Pieces that a segmentation break split apart are joined when their ends face each other, with the allowed gap scaled to the crack's width. A free end pointing into the side of another crack joins it as a junction. Bridged stretches are flagged in every output and drawn dashed.
- **End extension.** Free ends are carried out to the tip of the mask, which the skeleton stops one half-width short of.
- **Trunk and branches.** Every crack is split into its longest run (the trunk) and the branches off it, each with its parent.
- **Width along the crack.** The mask is sampled across the crack at every point and its edges found to sub-pixel; the same profile re-centres the line.
- **Smoothing on arc length.** Lengths are measured on a smoothed line, not the pixel staircase that overstates diagonals by up to 8%.
- **Corner fallback, fixed.** The v0.1 corner tracer is kept as `--method corners` and as the fallback in `auto`. Corners are now walked onto the centreline before they are linked, so a wide crack is traced down its middle rather than around its outline, and the spanning tree keeps its branches.
- **Physical units** with `--px-size`, and **width classes** (`--width-classes 0.1,0.3,1`) that report the length of crack in each width band.
- **Outputs**: per-image JSON with full geometry, a CSV row per crack, GeoJSON, SVG, overlays coloured by width, and plain centreline images.
- **`fine-tracing eval`** scores traces against reference centrelines with the buffer method (precision, recall, F1 within a tolerance), mean and 95th-percentile distance, length error, width error and junction recall.
- **`fine-tracing synth`** generates cracks with exact ground truth: centreline, width at every point, junctions and ends, a mask spoilt the way segmentation output tends to be, and a concrete-like photo.
- **`fine-tracing bench`** runs every tracer, v0.1 included, on the same synthetic cracks and writes tables and charts.
- **Python API**: `trace(mask, image=None, **settings)` returns a `TraceResult`; settings live in a `TraceConfig`.
- Tests for the graph, pruning, bridging, widths, mask formats, exports and the CLI, run on Python 3.9 to 3.12 in CI.

### Changed

- Settings are a `TraceConfig` object, CLI flags or a JSON file instead of module globals and environment variables.
- `fine-tracing run --frames-dir --masks-dir --output-dir` still works and maps to `fine-tracing trace`.
- Masks can be binary, grey, colour (red on black counts), RGBA or probability maps, with an optional hysteresis threshold.
- Dependencies: `scikit-image` added; `networkx`, `pandas` and `matplotlib` dropped from the core (matplotlib is only needed for benchmark charts).

### Fixed

- The v0.1 metrics paired cracks by centroid and compared x as a function of y, which broke on horizontal and branching cracks. Scores now use distances between point sets.
- ORB crashed on contours smaller than 32 px because the crop was resized but its mask was not.
- A mask passed as the frame was traced around its outline instead of down its centre.
- Hard-coded local paths in the experiment scripts; the scripts are gone, their ideas now live in the package.
