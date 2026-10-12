# Guitar finish simulator

## Latest full-guitar model

Open **`blender/full_guitar.blend`** for the complete instrument with the approved Sabre-style carve. Full-size front, three-quarter, rear, and carve-detail images of the rotated `20261009_112804.jpg` top are in `renders/full_guitar/hero/{prs_reference,extreme_black}`. Eight-top full-guitar grids for all four finishes are in `renders/full_guitar/contact_sheets`.

The earlier `blender/guitar.blend` and body-only grids retain the preceding body study. The full-instrument scene uses the updated continuous front/rear carve, 44 mm center thickness and 12 mm nominal rim before 2 mm edge rounding.


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

## Full-instrument specifications and reproduction

The PDF and supplied reference drawings are copied into `assets/references`. `config/full_guitar.json` contains the instrument dimensions and assumptions. The body retains the Umbraeternal outline; its front and rear rise smoothly from the thin rim to the center. The tapered body is a uniform constrained triangulation sampled from a smoothed physical distance field, with explicit surface normals and a closed manifold mesh. `geometry/full_guitar/body-section.svg` shows the nominal carve before perimeter rounding. `carved_body.obj` supplies the carved body, and the full `.blend` contains every editable component.

The full model includes:

- 647.7 mm (25.5 inch) scale; 22 stainless frets with 2.8 mm jumbo crowns.
- 41.9 mm nut, 55.5 mm target last-fret width, 241.3 mm (9.5 inch) fretboard radius.
- Satin maple fretboard, flush black blocks and Ankh, black binding and 2 mm white side dots.
- Three maple neck sections with two 2.5 mm walnut stripes; 21.5/22.5 mm neck thickness at frets 1/12, with an approximate rounded set-neck heel.
- Illustrated angled headstock with actual matching wood-photo veneer, black Tusq nut slots, six 9–46 strings and four left/two right tuners.
- Tuner exteriors based on the latest dimensioned drawing: 39 mm overall envelope, 15.5 mm housing and 22.9 mm fixing envelope. The rounded button silhouette is surveyed from that drawing; unprovided depths remain approximate.
- Gotoh-style recessed bridge: 83.5 × 40 mm plate, 54 mm string spread, 56 mm post pitch and 6 mm tremolo arm.
- Direct-mounted brushed black nickel humbucker covers and a black single-width middle pickup, black dome knobs, selector, strap locks, side barrel jack, rear covers and battery enclosure.

The manufacturer components are exterior visual models, not supplied factory CAD. Exact internal machining, rear routing, electronics, neck scan, set-neck engineering and headstock angle were not provided. The C profile and 12° headstock angle are provisional. Rear/sides are modeled with a dark glossy finish; the body timber species and its actual grain were not supplied. Neck/fretboard use plain maple color rather than fabricated grain. The matching headstock veneer samples a separate region of the same real photo at the same assumed physical scale; this does not prove a suitable remnant can be cut from the actual blank.

Reproduce the complete full-instrument package:

```sh
.venv/bin/python full_guitar_pipeline.py --blender /Applications/Blender.app/Contents/MacOS/Blender
```

Individual geometry and render commands:

```sh
.venv/bin/python prepare_full_guitar.py
/Applications/Blender.app/Contents/MacOS/Blender -b blender/guitar.blend --python-exit-code 1 --python blender/scripts/full_guitar.py
/Applications/Blender.app/Contents/MacOS/Blender -b blender/full_guitar.blend --python-exit-code 1 --python blender/scripts/render_full_guitar.py -- --preset prs_reference --camera all
/Applications/Blender.app/Contents/MacOS/Blender -b blender/full_guitar.blend --python-exit-code 1 --python blender/scripts/render_full_guitar.py -- --preset all --all --comparison
.venv/bin/python full_guitar_comparisons.py
```

Use `--candidate SOURCE.jpg` for a specific top, `--preview` for quick iterations, and `--camera front|perspective|rear|carve` for a single view. The batch renderer updates body and headstock materials together. To save a configured finish/candidate into the editable full scene:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b blender/full_guitar.blend --python-exit-code 1 --python blender/scripts/save_full_finish.py -- --preset extreme_black --candidate 20261009_112804.jpg
```

Body/headstock controls are editable in the Shader Editor. CLI runs reapply `config/finishes.json`; manual body-material edits require matching edits to the copied headstock material, or the renderer's synchronization step. Hardware objects and cameras remain separate editable objects.

Actual full-instrument execution uses Blender 5.2.2 LTS and Cycles, fixed exposure 0 and seed 17. Full-size views use 64 samples: front/rear 1100 × 2600, perspective 1800 × 2200, carve detail 1600 × 1600. Comparisons use 48 samples at 800 × 1800. All candidates share geometry, camera fixtures, lights and exposure. Scene signatures include vertices, faces, UVs, normals, modifiers, object transforms, light settings, camera settings and color management.

`blender/full_guitar/validation.json` records measurements on the saved model: 44.000 mm center thickness; 21.503/22.497 mm neck thickness; 41.900 mm nut; 55.461 mm last-fret width (within 0.1 mm of target); correct fret positions and radius; 4L/2R tuners; correct bridge envelope; positive string-to-fret clearance. The body has 17,457 vertices and 30,280 faces with zero nonmanifold edges. `renders/full_guitar/validation.json` verifies all 32 comparison images and eight full-size views against the reopened scene signature and original-photo hashes. Execution logs are in `blender/full_guitar`.

## Softer material reflections with the original studio rig

The original five studio lights are restored: key/fill 6/3 W, headstock rim 3 W, rear key/fill 8/3 W, world strength 0.25. Softboxes remain visible to glossy rays; there are no hardware-only lights. Exposure, cameras, geometry, and photograph placement are fixed.

All four finish presets now use coat weight 0.12, coat roughness 0.24, base roughness 0.32, and Specular IOR Level 0.15. These artistic satin finish controls reduce the broad reflection over the wood while retaining soft curvature highlights. Stain palettes and photograph-derived figure are unchanged. Body and photographed headstock veneer share the controls; hardware and neck retain their existing materials. Earlier body-only renders are historical and require rerendering to show the new material controls.

Apply lighting and save the selected material without rebuilding geometry:

```sh
/Applications/Blender.app/Contents/MacOS/Blender -b blender/full_guitar.blend --python-exit-code 1 --python blender/scripts/update_full_lighting.py
/Applications/Blender.app/Contents/MacOS/Blender -b blender/full_guitar.blend --python-exit-code 1 --python blender/scripts/save_full_finish.py -- --preset prs_reference --candidate 20261009_112804.jpg
```

Regenerate images with `render_full_guitar.py`, then refresh sheets with `full_guitar_comparisons.py`. Lighting visibility/linking settings are included in the common scene signature.

## Specification-driven workbench

The reusable workflow runs entirely locally, with no LLM, image generation, remote inference or stock textures. It accepts a versioned JSON specification, 2D CAD contours, real wood photographs and a finish-reference photograph. Human calibration supplies crop corners, bookmatch classification and finish choices that a single photograph cannot determine uniquely.

Run from this checkout using the existing Python environment and Blender 5.2.2 LTS. `--blender /path/to/blender` or the `BLENDER` environment variable selects another installation; an executable on PATH is discovered automatically. The tested host Python is 3.14. Dependencies remain the four packages in `requirements.txt`.

```sh
.venv/bin/python simulate.py validate projects/umbraeternal/project.json --workspace .work/umbraeternal
.venv/bin/python simulate.py prepare projects/umbraeternal/project.json --workspace .work/umbraeternal
.venv/bin/python simulate.py build projects/umbraeternal/project.json --workspace .work/umbraeternal
.venv/bin/python simulate.py render projects/umbraeternal/project.json --workspace .work/umbraeternal --preset prs_reference --candidate 20261009_112804.jpg --view carve --preview
.venv/bin/python simulate.py batch projects/umbraeternal/project.json --workspace .work/umbraeternal
.venv/bin/python simulate.py serve projects/umbraeternal/project.json --workspace .work/workbench --port 8765
```

Open `http://127.0.0.1:8765`. The editor supports draggable crop corners (and a numeric JSON alternative), automatic/manual seam alignment, board-edge orientation for simulated pairs, physical texture scale, placement rotation/translation, selected reference-color regions, stain/burst/surface controls, specification editing and actual Blender previews. It saves a separate calibration draft at `.calibration/project.json` inside the chosen workspace. Reusing that workspace resumes the draft; use a new workspace for a different project. A running preview holds its inputs fixed until completion. Source photographs and the original project specification remain intact.

To batch a saved calibration, supply its draft as the specification:

```sh
.venv/bin/python simulate.py batch .work/workbench/.calibration/project.json --workspace .work/calibrated-delivery
```

The ordinary `build` creates a shader-only `blender/material_template.blend`, then constructs the final instrument once. Finishes reuse that instrument. Hashes verify cached artifacts, so a corrupt scene is rebuilt; finish/placement-only edits reuse geometry. Explicit `render` commands also save `blender/last_render.blend` with the selected photograph, body/headstock finish and active camera. The cached `blender/full_guitar.blend` retains the project's default configuration. Existing body-only and full-guitar legacy scripts remain available.

The complete batch produces all candidate × finish front comparisons, four default-instrument views for PRS/extreme-black, and an enlarged PRS carve view for every candidate. The default candidate's PRS carve view serves both purposes. `--no-hero` omits the default-instrument views while retaining comparisons and enlarged PRS views. Delivery checks inspect image dimensions, scene signatures, common comparison settings, source/texture hashes and current finish controls before making contact sheets.

### Project specification

`projects/umbraeternal/project.json` reproduces the approved instrument. `projects/compact/project.json` is a second regression fixture: a 304 mm body derived from a 95% scale of the supplied CAD, 635 mm scale, 24 frets, 42/14 mm carve and one physical quilt candidate. It demonstrates reuse without claiming a separately engineered instrument design.

Paths resolve beside the specification, not the shell's working directory. `config.surface`, `config.instrument`, `config.finishes` and `inputs.candidates` accept either a JSON-file path or an inline object. Start by copying an example and changing its paths and dimensions. Specifications must declare `version: 1`.

| Input | Contract |
|---|---|
| `inputs.photos` | Directory containing the unchanged source filenames. One photograph per candidate. |
| `inputs.candidates` | Crop specifications keyed by source filename. `physical` requires two surveyed halves in the same photograph; `simulated` requires one board. |
| `inputs.finish_reference` | Actual finish-reference photograph; used for human-selected palette samples. |
| `inputs.design_reference` | Required only for the legacy headstock-image fallback. New designs should supply headstock CAD. |
| `geometry.body` | `path`, explicit `units`, optional `layer` and `origin_mm`. Body x=0 is the string centerline; Cartesian +y points toward the neck. |
| `geometry.headstock` | Optional CAD contour, x=0 on its centerline and y=0 at the nut, +y toward the tip. |
| `geometry.anchors` | Optional named DXF POINT layers for bridge, pickups and controls, with explicit units and coordinate frame. |
| `config.surface` | Body width, texture domain, burst-distance settings and per-candidate placements. |
| `config.instrument` | Scale, fret/neck/body dimensions, carve/rounding, bridge dimensions, studio lights, render settings and assumptions. |
| `config.finishes` | Independent stain, burst and surface parameters; the four supplied preset identifiers support the standard batch. |

CAD import supports closed, straight-segment ASCII DXF `LWPOLYLINE` contours and SVG `polygon` elements. Use named `BODY` and `HEADSTOCK` layers/ids, or declare another name. Export curves as a sufficiently dense polyline; curved DXF bulges, SVG paths/transforms, holes and general 3D CAD are rejected or outside this version's contour contract. Units are `mm`, `cm`, `m` or `in`; SVG y is converted from screen coordinates to Cartesian coordinates. Body width must agree with the specification rather than being silently stretched.

Optional hardware anchors use DXF `POINT` entities on layers `BRIDGE`, `NECK_PICKUP`, `BRIDGE_PICKUP`, `SINGLE_PICKUP`, `VOLUME`, `TONE` and `SELECTOR`. Bridge/pickups must lie on x=0. Anchor `frame: "cad"` (default) uses the body drawing's coordinates and recenters y with the body; `frame: "body_center"` uses already-centered model coordinates. `origin_mm` is subtracted after unit conversion. Controls accept x/y; bridge and pickup anchors supply y. Effective locations are saved in `geometry/hardware-anchors.json` and `config/full_guitar.json`.

This version uses the existing six-string HSH, 510-style bridge and 4L/2R tuner geometry family. It supports different body/headstock contours, scale, fret count, neck/body dimensions and the tested bridge/anchor controls. Routing, set-neck heel and undimensioned hardware details remain visual approximations. New hardware families need additional geometry adapters and measurements. The legacy image fallback assumes the original Umbraeternal illustration layout. The surveyed final tuner silhouette overrides earlier provisional button dimensions retained in the legacy configuration.

### Wood and finish calibration

Crop corners are `[top-left, top-right, bottom-right, bottom-left]` in original photo pixels. Physical pairs list left and right halves in that order. Quarter-turn crop rotation aligns the board; `seam_edge` chooses the mirrored edge for a single board. `alignment_shift_px` overrides automatic vertical registration within the conservative overlap limit; leaving it absent restores automatic alignment. Both physical halves remain in the result.

Candidate `width_mm` overrides the assumed width of the finished, usable bookmatch crop. Its height is inferred from rectified pixel aspect. This changes physical sampling scale without resampling grain; it is not independent verification of cutting feasibility. Positions use `x_mm`, `y_mm` and `rotation_deg` in `surface.placements`: the body coordinates are rotated about the seam center, then translated within the photo. Placements outside the photographed blank are rejected instead of extending edge pixels into invented coverage.

Reference samples suggest four palette colors using median pixels inside selected regions. Reflections, unknown exposure and image processing remain in those samples; they do not recover dye absorption or clearcoat properties. Human preview adjustment is required. Stain/burst controls never change the studio rig, and surface controls do not repaint the grain. Single-photograph chatoyance and unfinished-versus-finished wood remain the optical limitations described above.

Optional instrument render-profile overrides are `preview_front_resolution`, `preview_perspective_resolution`, `preview_carve_resolution`, `preview_samples`, `comparison_front_resolution`, `comparison_samples` and `carve_resolution`. Existing `front_resolution`, `perspective_resolution` and `samples` control full-size views. All comparison panels share one profile; enlarged PRS delivery requires at least 1600 × 1600.

### Artifacts, verification and refactoring evidence

Each workspace contains copied source/CAD inputs, editable configuration, corrected/bookmatched textures and provenance, physical perimeter/carve fields, OBJ geometry, packed Blender projects, image-level render records, stage logs/execution receipts, contact sheets and validation reports. `project.lock.json` records resolved inputs/configuration and source hashes; `project.snapshot.json` points to copied local inputs so the workspace can recreate another project without original absolute paths.

The reusable package is under `src/guitar_finish_simulator`: `project` defines inputs, `cad` imports contours/anchors, `wood` prepares photographs, `geometry` prepares physical fields/coverage, `finishes` validates material controls, `rendering` adapts Blender rendering, `pipeline` executes/caches stages, `calibration` persists human adjustments, `app` serves the local editor and `delivery` validates/makes comparisons. Blender construction remains in `blender/scripts` behind those interfaces.

Run the fast public-boundary checks or the complete suite with real Blender execution:

```sh
.venv/bin/python verify.py
.venv/bin/python verify.py --rendering
```

The complete suite builds/reopens the approved and compact instruments, exercises named CAD anchors, checks manifoldness and measured dimensions, compares flame/quilt renders to captured approved images, verifies exact wood texture/provenance reproduction, repairs corrupted cached scenes, tests material edits without geometry/studio changes, checks saved preview materials, runs the HTTP preview job and executes a complete compact finish batch. No Blender tests are silently skipped. `BLENDER=/path/to/blender` selects the test executable.

`verify.py` writes `.work/verification/report.json` with executed counts, failures/skips, pipeline code hash, saved-model evidence and golden-image error metrics. Tests allow mean RGB error below 0.15/255 and 99th-percentile error below 2/255. Exact scene signatures enforce invariants within batches; tiny Blender primitive indexing/UV differences across fresh builds are checked through measured geometry and golden renders. `REFACTORING.md` records the red/green checkpoints and behavior-preserving extractions.
