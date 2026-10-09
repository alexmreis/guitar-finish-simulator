# Project instructions

Read `TASK.md` before implementing, changing, or validating the pipeline. It is the authoritative specification for stages, deliverables, finish targets, and acceptance criteria.

## Core constraints

- Use actual supplied wood photographs and deterministic image processing. Never use generative imagery, synthesized grain, generative fill, or stock textures.
- Generate guitar geometry once and reuse it unchanged across candidates and finishes. Keep comparison cameras, lighting, exposure, scale, and placement fixed.
- Preserve source filenames and wood features. Preserve both photographed halves of physical bookmatches; explicitly label mirrored single boards as simulated bookmatches.
- Keep dimensions, crop transforms, texture placement, and finish controls configurable. Record assumptions when physical measurements are unavailable.
- Execute Blender for actual 3D renders. Report execution evidence; a script alone is not a completed rendering pipeline.

## Workflow

1. Inspect supplied assets and execution capabilities. Identify all eight candidates and both design and finish references. If essential assets are missing, report the exact missing inputs rather than inventing substitutes.
2. Follow the six stages in `TASK.md`, executing code and inspecting outputs at each stage. Save editable intermediate assets and diagnostics.
3. Validate silhouette fidelity, mesh manifoldness, UV alignment, texture provenance, and invariant comparison settings before batch rendering.
4. Complete all four finish comparisons and the enlarged PRS-inspired renders. Verify the saved Blender project opens and the documented commands reproduce outputs.
5. Report actual Blender version, engine, mesh vertex count, render settings, validation results, and any unmet acceptance criteria.

## Repository conventions

Use the deliverable layout in `TASK.md`. Use Blender Python for scene construction and rendering, and OpenCV/Pillow/NumPy or equivalent deterministic libraries for photograph processing. Keep dependencies minimal and CLI workflows configuration-driven.

Document setup, commands, material controls, measurement assumptions, and single-photograph optical limitations in `README.md` as implementation becomes available. Derive validation evidence from executed code and inspected artifacts.
