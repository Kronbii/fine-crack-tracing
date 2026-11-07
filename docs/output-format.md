# Output format

`fine-tracing trace` writes one JSON file per image, a CSV row per crack, and optionally GeoJSON, SVG, overlays and centreline images. `TraceResult.to_dict()` in Python returns the same JSON structure.

Coordinates are image pixels: `x` to the right, `y` down, with `(0, 0)` at the centre of the top-left pixel, so a line can reach `-0.5` at the image edge. Lengths and widths are in pixels unless a field name ends in a unit. When `--px-size` is given, each pixel measurement also gets a copy in that unit (`length_mm`, `max_width_mm` and so on, for `--unit mm`). A value that could not be measured is `null`.

## Per image: `json/<image>.json`

```json
{
  "image": "wall-609",
  "width": 1512,
  "height": 2016,
  "px_size": 0.16,
  "unit": "mm",
  "summary": { ... },
  "cracks": [ { ... }, ... ],
  "timing_ms": { "clean": 41.2, "trace": 68.9, "graph": 3.1, "measure": 58.0, "total": 171.2 },
  "config": { ... every setting used ... },
  "version": "1.0.0"
}
```

### `summary`

| field | meaning |
|---|---|
| `cracks` | number of cracks |
| `length_px` | total traced length, bridged stretches included |
| `max_width_px` | the widest point of any crack |
| `median_mask_width_px` | median width of the mask along its skeleton, a rough scale for the image |
| `bridged_gaps` | number of breaks in the mask that were joined |

### Each crack

| field | meaning |
|---|---|
| `id` | 1, 2, ... from longest to shortest |
| `method` | `skeleton`, or `corners` where the fallback traced it |
| `pattern` | `single` (one path), `branched` (a trunk and branches), `network` (it has loops) |
| `length_px` | length of all its paths, bridged stretches included |
| `gaps`, `gap_px` | how many breaks were bridged, and their total length |
| `mean_width_px`, `median_width_px`, `p95_width_px` | width statistics, weighted by length; junction zones and bridges left out |
| `max_width_px` | widest point, read from a lightly filtered profile so a single ragged sample does not set it |
| `branches`, `junctions`, `endpoints`, `loops` | its shape as a graph |
| `orientation_deg` | direction of the trunk, degrees counter-clockwise from the image x axis, 0–180 |
| `direction` | `horizontal`, `vertical` or `diagonal`, from `orientation_deg` |
| `tortuosity` | trunk length divided by the straight distance between its ends |
| `area_px` | mask pixels in the components it was traced from |
| `bbox` | `[x0, y0, x1, y1]` of its paths |
| `junction_points`, `endpoint_points` | `[x, y]` of each junction and free end |
| `length_w<...>` | with `--width-classes`: length whose width falls in each class |
| `paths` | its trunk and branches, below |

### Each path

| field | meaning |
|---|---|
| `id` | 0 is the trunk; branches follow |
| `parent` | the path this one branches off, or `null` for the trunk |
| `order` | 1 for the trunk, 2 for a branch off it, 3 for a branch off a branch |
| `length_px` | length of this path |
| `points` | `[x, y]` every `--step` px (1 by default) along the centreline |
| `width_px` | width across the crack at each point; `null` at junctions and on bridges |
| `bridged` | one 0/1 per segment between consecutive points: 1 where it crosses a break in the mask |

## All images: `cracks.csv`

One row per crack, with the same fields as the crack record above apart from the point lists and paths, plus the `image` it came from.

## `geojson/<image>.geojson`

A FeatureCollection in image pixel coordinates (not geographic ones). Each path is a `LineString` with `crack`, `path`, `parent`, `order`, `method`, `length_px`, `gap_px`, `mean_width_px` and `max_width_px` properties; each junction is a `Point` with `crack` and `kind: "junction"`.

## The rest

| file | contents |
|---|---|
| `svg/<image>.svg` | the paths as vector polylines coloured by width, bridges dashed, junctions ringed |
| `overlays/<image>.jpg` | the lines drawn over the photo (or over the mask, as `.png`, when there is no photo) |
| `centrelines/<image>.png` | the lines alone, white on black, one pixel wide, for other tools or for `fine-tracing eval` |
| `summary.json` | per-image summaries, the mean time per image, and the settings used |

## Reference files for `fine-tracing eval`

`eval` reads either this tool's JSON or a centreline image (white on black) on both sides. A hand-made reference can be a drawing of each crack's centreline, or a JSON file in the same shape as above: `cracks` → `paths` → `points`, with optional `width` (or `width_px`) per point and optional `junctions` per crack. The synthetic generator writes its ground truth in that shape.
