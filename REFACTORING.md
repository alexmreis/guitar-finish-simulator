# Reusable pipeline implementation record

The user confirmed tests at these public boundaries: specification/CAD import, prepared photograph artifacts and provenance, saved Blender scene, rendering CLI and comparison settings.

Use small behavior-preserving refactorings, with a green checkpoint before the next change. Introduce new behavior through one failing public-interface test at a time. No LLM or generated wood imagery is part of runtime.

## Baseline

- Commit `f4cb9dc` is the approved full-instrument implementation.
- Captured 70 artifact hashes; stage-one checks exclude two historical diagnostic reports produced outside the preprocessing CLI.
- Fresh Cycles carve previews: physical flame 20261009_112804.jpg and physical quilt 20261009_113155.jpg, 1000 × 1000, 24 samples, seed 17.
- Pixel comparison permits mean absolute RGB error < 0.15/255 and 99th percentile < 2/255, allowing tiny renderer differences while detecting visible drift.

## Checkpoints

1. Characterize existing preprocessing CLI and real Blender renderer: pass.
2. Extract `prepare_wood(root, input_dir)` and retain the old CLI: exact texture/provenance checks and real render regression pass.

## Planned vertical slices

- Versioned project specification and isolated workspace, preserving legacy entry points.
- Validated 2D CAD contours with explicit units and carve inputs.
- Configurable geometry and reusable hardware layout with saved-model measurements.
- Independent finish calibration and bounded wood placement controls.
- CLI stage caching, provenance, preview/delivery workflows, local calibration UI.
- Second project build, full comparison delivery, reproduction documentation.
3. Project specification/materialization: observed failing import, implemented isolated inputs, and observed failing invalid-carve test before adding rejection. All checks pass.
4. Workspace selection: observed missing outputs under `GFS_PROJECT_ROOT`, added path injection to photo and Blender entry points. Golden textures and both real renders pass with outputs outside the repository.
5. CAD import: red/green tests for actual BODY DXF, rejection of open/crossing contours, and SVG inch conversion. Supported inputs are closed straight-segment DXF LWPOLYLINE and SVG polygon; unsupported curves/transforms fail explicitly.
6. Extract shared perimeter fields: outline, DXF and perimeter PNG remain byte-identical. Existing uv-layout.png is overwritten by later validation, so it is not used as an extraction-stage baseline.
7. Specification → isolated preparation → actual Blender build/reopen: 17,457 body vertices, zero nonmanifold edges. Both rebuilt flame/quilt previews are pixel-identical to approved renders. Full-scene hashes differ across fresh builds because Blender generates different selector-sphere face indexing and ~1e-7 nut UV differences. Golden renders/measurements verify cross-build behavior; exact signatures still enforce invariants within each batch.
8. Variable candidate count and specification dimensions: observed legacy candidate-index failure, then fixed center/fret/neck/bridge checks to measure against supplied dimensions. Compact 304 mm CAD body / 635 mm scale / 24 frets / one physical quilt builds and reopens successfully.
9. Render CLI and cache: render records include finish controls and photograph/texture hashes. A verified model is reused; deliberate .blend corruption triggers rebuild and revalidation. An actual material-change test verifies changed reflections with identical scene signature and unchanged cached model timestamp.
10. Calibration: red/green tests for reference-region sampling, persistent draft finishes, invalid-control rejection, two-half physical bookmatches and crop bounds. Loopback HTTP editor and asynchronous preview tested against actual Blender; native Chrome inspection confirms controls and completed preview.
11. Delivery: dynamic candidate counts, all-finish matrix, minimum 1600-square enlarged PRS views, source/texture/control provenance, fixed settings and contact sheets. Compact CLI batch executes successfully.
12. CAD anchors: DXF POINT layers place bridge/pickups/volume/tone/selector. Saved model measurements verify bridge and volume placement. Original rebuilt flame/quilt renders still meet the approved golden baseline.
13. Portable project snapshot: all photograph/reference/CAD inputs are copied and can materialize a second workspace without original paths.
14. Wood physical scale and placement: explicit blank width changes metadata/physical mapping without resampling grain; a placement that would extend pixels outside the photographed blank is rejected before Blender construction.
15. Extract full render loop into `rendering.render_instrument`: legacy saved-scene and fresh-build flame/quilt regressions pass before subsequent changes.
16. Render profiles: observed 1000-square/24-sample output for a requested 256-square/8-sample preview, then made profiles configurable and verified actual output.
17. Last-render scene: observed missing saved scene, then stale headstock candidate/preset after reopening. Save a separate packed scene and synchronize body/headstock provenance; reopen test and golden regression pass. Specular-level value nodes now drive their editable shader input.
18. Shader-only bootstrap: observed absence of template evidence, then Blender discarding an unused material across save/reopen. Preserve the material datablock with a fake user, bootstrap zero mesh objects, construct the final body once and verify golden render behavior.
19. Carve domain/section diagnostics: observed hard-coded -200 mm origin for a 600 mm domain; domain, image normalization and section labels now follow project settings. Existing default render regression remains required.
20. Mixed valid/unknown candidate request: observed silent partial rendering; reject unknown filenames before constructing outputs.

## Executed final verification

`verify.py --rendering` executed 34 tests in 246.092 seconds: zero failures, errors or skips. The freshly rebuilt flame and quilt previews have mean and 99th-percentile RGB error of 0.0 against the approved baseline. Blender 5.2.2 LTS / Cycles reopened the instrument: 17,457 body vertices, zero nonmanifold edges, 44.00003 mm measured center and verified neck/fret/string/bridge dimensions. Machine-readable evidence is in `reports/refactoring-verification.json`.

The local editor was inspected in native Chrome, including actual preview completion. Its saved calibration draft was hashed before/after the server restart and remained unchanged. Development/batch outputs stay under ignored `.work/` workspaces; approved historical root renders remain intact.
