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
