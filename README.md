# Guitar finish simulator

A deterministic photo-to-Blender pipeline for the eight supplied maple candidates. Actual photographs supply the grain; a single fixed body mesh supplies the silhouette; shader controls supply the finish. No generated imagery or synthesized wood is used.

## Open the project

Open `blender/guitar.blend` in Blender 5.2.2 LTS. Source textures for the initially selected material are packed. The complete folder supplies all other candidates for batch rendering. Front, Perspective, and Detail cameras are available. Hardware objects are separate and hidden from renders by default; pickup pockets remain visible.

Select **Guitar Body**, open the Shader Editor, and edit the named Value nodes in its material. These control dye intensity, sandback strength, figure contrast, highlight brightness, warmth, darkness, burst width, edge hold, edge/inner opacity, burst exponent, transition position, clearcoat, roughness, IOR, and optional bump. The ramp exposes four stain colors; the burst Mix node exposes its independent color. These edits affect interactive renders; update `config/finishes.json` to preserve changes for CLI rendering, which reapplies presets. Run `save_finish.py` against the existing `.blend` to save a configured preset into the editable scene without rebuilding geometry.

## Reproduce

Original inputs are retained at the root and copied/extracted into `assets/originals` and `assets/references`. With Python 3.14 and Blender installed:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python pipeline.py --blender /Applications/Blender.app/Contents/MacOS/Blender
```

This preprocesses all photos, extracts the outline, builds and saves geometry once, renders 32 combinations, produces geometry diagnostic views, reopens and validates the scene, and builds four comparison sheets. It exits on a failed stage.

Individual stages:

```sh
.venv/bin/python preprocess.py --input assets/originals
.venv/bin/python extract_outline.py
/Applications/Blender.app/Contents/MacOS/Blender -b --python-exit-code 1 --python blender/scripts/build.py
/Applications/Blender.app/Contents/MacOS/Blender -b blender/guitar.blend --python-exit-code 1 --python blender/scripts/render.py -- --preset prs_reference --all
.venv/bin/python comparisons.py
```

Use `--candidate 20261009_113155.jpg` to select a blank, `--resolution 800` for a preview, and `--camera Perspective` or `--camera Detail` for alternate views. Preview renders with the Front camera overwrite that preset/candidate's output, so regenerate its full-resolution render before validation. PRS-inspired outputs default to 1600 × 1600; other presets default to 800 × 800. `--preset all --all --diagnostics` produces the complete batch and model views.

## Inputs and positioning

`config/candidates.json` contains manually surveyed crop quadrilaterals, bookmatch status, and orientation. Physical pairs are `112804`, `112900`, `113100`, and `113155`; singles are `111903`, `111941`, `113621`, and `113831` (each with the `20261009_` prefix and `.jpg` suffix). Physical halves receive independent homographies. Rectified halves are center-cropped to a shared height and seam-adjacent width, preserving their separate photographed figure. The central background gap in the third physical pair is excluded. Single boards rotate 90° before being mirrored; their long grain direction becomes the guitar's long axis. `seam_edge` selects the board edge opening at the join. `20261009_111941.jpg` uses the left edge after rotation so its strongest flame lies toward the body center, rather than the outside scrap. Physical flame pairs are registered by seam-adjacent dark-band correlation; the quilted pair uses a narrower seam neighborhood to align cell boundaries. Only vertical shifts and overlap crops are applied (2, -10, -3, and -2 pixels respectively); both photographed halves remain intact. Metadata records the shifts and before/after correlation. `alignment_shift_px` overrides automatic registration within its conservative limit.

Every filename remains embedded in asset and render names. The `.jpg.png` suffix denotes a PNG derived from that exact JPEG source. Metadata records source SHA-256, corners, homographies, orientation, seam, assumed dimensions, and conservative correction bounds. Crop diagnostic PNGs show the editable boundary selections. Unmodified color crops, corrected images, bookmatches, and figure maps remain available. `source-crop.png` is the uncorrected rectified crop (a single board for simulated candidates); `original-crop.png` is the raw rectified bookmatch used in the comparison panels.

Illumination normalization changes gain by at most ±6%; per-channel color adjustment is capped at ±3%. Percentile-scaled luminance/local contrast drives the figure map, which is an artistic finishing proxy. `20261009_112804.jpg` uses the configurable `horizontal_flame` figure filter: it emphasizes the photographed horizontal curl bands and retains 12% fine-grain response, preventing vertical preparation/longitudinal lines from dominating its stain. Neither half is rotated independently, and its original albedo is unfiltered. For this known light physical bookmatch, `balance_figure_halves` calibrates the curl mask separately on each half using its interior 2nd/98th percentiles. This prevents photographed contrast differences from being exaggerated into unequal stain darkness. It changes the artistic dye-response proxy, preserves both photographed patterns, and records each calibration range in the metadata; it is not a measurement of dye absorption. Knots, spalting, pencil marks, and existing glare remain present. No inpainting is used.

No physical blank dimensions were supplied. Each bookmatch is provisionally assumed to be **400 mm wide**, with height derived from its rectified pixel aspect ratio. This is an isotropic visual-study scale, not proof that a blank can make a real top. Source image resolutions differ, and camera aspect recovery without measurements remains approximate. Supply measured dimensions before making a cutting decision. Texture size stays in physical units and is never independently stretched horizontally and vertically to fit the body.

`config/project.json` controls body dimensions, UV domain, resolutions, sampling, hardware visibility, and blank placements. A placement entry looks like:

```json
"placements": {
  "20261009_113155.jpg": {"x_mm": 0, "y_mm": 0, "rotation_deg": 0}
}
```

Rotation occurs about the center of the blank in physical coordinates. Placements align the bookmatch seam to the fixed guitar centerline. `20261009_112804.jpg` currently uses a 180° rotation of the complete physical bookmatch; the comparison texture panel shows that chosen orientation. Translations/rotations intentionally change that proposed cutting position. Scene validation rejects placements extending outside photographed wood.

## Geometry and burst

The outline comes from OpenCV foreground contour extraction of the front illustration, resampled and fitted to a periodic spline. The editable neck-exclusion rectangle closes the unseen body/neck interface provisionally; hardware strap pins are excluded. `geometry/silhouette-overlay.png` and `spline-comparison.png` show the source comparison. Dimensions are 320 mm maximum outline width, approximately 440 mm height, and 44 mm thickness. DXF units are millimeters. SVG and outline JSON preserve editable geometry; OBJ exports the finished body in meters.

The manifold body has rounded perimeter edges, an approximate forearm slope, a shallow rear belly contour, and two approximate pickup pockets. Pickup, bridge, and control placements follow the illustration. This is a finish-study body, not a production-ready neck joint or internal routing design. The illustration provides no measured three-dimensional contour depths. Pocket/contour depths and edge rounding are provisional.

A planar UV projection gives a fixed centerline and no in-plane skew. `uv-layout.png` shows the silhouette domain; `uv-mesh.svg` shows actual top mesh UV edges. Front curvature changes surface distances slightly, as a real contour would, while all candidates share the same projection.

The burst uses an exact Euclidean distance field from the extracted silhouette, including concave cutaways. Distance is normalized against each horizontal wood span's half-width, with a configurable 100 mm minimum to keep the burst broad around narrow horns. `edge_hold` retains an outer black region, then smoothstep fades toward the center. The PRS-inspired preset uses full edge opacity and a near-black `#020304` burst. Gloss highlights can still reflect off black clearcoat. The distance field is geometry-derived, not an ellipse and not part of the photographed wood.

Dye/sandback is approximated by contrast, a luminance exponent, and a four-color ramp. The PRS-inspired preset retains neutral charcoal shadows but uses muted maple-beige highlights (`#8E806D` and `#B8A48A`), matching the warmer light veins in the supplied PRS photograph. Extreme Black uses the same maple-beige highlight palette at its lower brightness and overall darkness; Dark Charcoal retains its neutral palette. It does not infer measured dye absorption. Clearcoat is a separate Principled BSDF layer. Bump is disabled by default; its optional depth is limited to 0.03 mm before strength scaling. Single photographs cannot recover directional chatoyance or separate all illumination from the wood's albedo.

## Outputs and verification

- `renders/comparisons/preprocessed.png`: all eight prepared bookmatches.
- `renders/comparisons/{natural,charcoal,prs_reference,extreme_black}.png`: source filename, raw rectified bookmatch, rendered body, preset, and physical/simulated status.
- `renders/prs_reference/*.jpg.png`: eight 1600 × 1600 front renders.
- `renders/calibration/reference-comparison.png`: supplied PRS photo alongside flamed/quilted study renders. Its lighting and image processing are unknown; calibration is visual rather than a measured material match.
- `geometry/model-{front,perspective,detail}.png`: model inspection views.
- `blender/build.log`, `calibration.log`, and `batch.log`: actual Blender execution evidence.
- `geometry/mesh-validation.json`, `outline-validation.json`, `blender/scene-validation.json`, and `renders/validation.json`: validation records.

Actual execution uses Blender **5.2.2 LTS**, **Cycles**, 32 samples, denoising, seed 17, AgX with Medium High Contrast, fixed exposure 0, and a fixed orthographic front camera. The saved body has 35,748 vertices and 71,339 faces, with zero nonmanifold edges after validated boolean repair. Each render records a SHA-256 signature covering mesh coordinates, polygons, UVs, corner normals, body transform, camera, exposure, and lights. All 32 front renders must share this signature. PRS render size, all source hashes, and all candidate/preset pairs are checked when producing the grids.

Exact cross-version or cross-device byte identity is not guaranteed by Cycles/denoising. The presets, geometry, inputs, seed, camera, and exposure are reproducible; keep the same Blender version for closest repeatability.

A repeated Natural Gloss render of `20261009_113155.jpg` produced identical decoded pixels on this machine. PNG byte hashes differed because the file metadata differed; `renders/repeatability/validation.json` records the measured pixel difference.

Save a configured finish into the existing project:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b blender/guitar.blend --python-exit-code 1 --python blender/scripts/save_finish.py -- --preset prs_reference --candidate 20261009_113100.jpg
```

The top uses analytically computed normals from the modeled forearm contour, preserving pocket-wall and perimeter normals. This prevents straight shading creases and false diagonal bands caused by interpolating normals over irregular triangles. A uniform-gloss regression probe in `blender/debug/line_probe.py` checks the reported waist region independently of the wood texture.
