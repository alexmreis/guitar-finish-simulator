# Project: Photorealistic Guitar Top Finish Simulator

You are a senior technical artist, computational graphics engineer, and Blender Python developer.

Your task is to build a **real, reproducible 3D rendering pipeline** to evaluate eight specific figured-maple guitar tops with different transparent stain and burst finishes.

**Do not use generative AI image models to produce the renders.** Do not recreate or hallucinate wood patterns. The entire point of this project is to preserve the actual grain of the photographed pieces, maintain identical guitar geometry across renders, and simulate different finishes through physically plausible materials.

Implement, execute, test, and deliver the working pipeline. Do not stop after producing scripts or describing an implementation.

## 1. Input assets

The following files are supplied:

- `drafttops.zip` — eight photographs of actual figured-maple pieces, plus an `Umbraeternal.JPG` guitar design reference.
- `Umbraeternal.JPG` — front and rear orthographic-style illustrations of the guitar.
- PRS SE Special Semi-Hollow reference photograph — target appearance for the finish.

All eight maple candidates must be processed, including the four rectangular bookmatched sets and four individual boards that require simulated bookmatching.

Preserve the original filenames in generated assets and the comparison results.

Inspect the actual files before making assumptions about their contents or dimensions.

## 2. Deliverables

Create a self-contained project with the following structure:

```text
guitar-finish-simulator/
├── assets/
│   ├── originals/
│   ├── textures/
│   │   ├── corrected/
│   │   ├── bookmatched/
│   │   └── processed/
│   └── references/
├── geometry/
│   ├── body_outline.svg
│   ├── body_outline.dxf
│   └── body_mesh.obj
├── blender/
│   ├── guitar.blend
│   └── scripts/
├── renders/
│   ├── natural/
│   ├── charcoal/
│   ├── prs_reference/
│   └── comparisons/
├── config/
│   └── finishes.json
├── README.md
└── requirements.txt
```

Produce:

1. A Blender scene containing the actual modeled guitar body, UV mapping, materials, lights, and camera.
2. One corrected wood texture for each original photograph.
3. One bookmatched texture for each candidate.
4. Eight renders per finish preset, all with identical geometry and camera framing.
5. A contact sheet comparing the eight tops for each finish.
6. An interactive Blender project where finish parameters can be adjusted and renders regenerated.
7. A Python command-line workflow for batch rendering.
8. A README explaining setup, rendering, material controls, limitations, and assumptions.

Save editable intermediate assets, not just final PNGs.

## 3. Body geometry reconstruction

Extract the body outline from the supplied Umbraeternal front-view illustration.

The illustration contains the neck, fretboard, pickups, bridge, controls, and body. Isolate the body's outer silhouette without allowing the neck or hardware to alter its shape.

Use OpenCV, contour detection, and spline fitting, supplemented by manually specified control points where necessary.

Requirements:

- Preserve the asymmetric Sabre-style double-cutaway silhouette.
- Preserve the precise relative horn lengths and cutaway depths.
- Preserve the waist and lower-bout proportions.
- Maintain a fixed centerline.
- Produce a clean, closed, non-self-intersecting outline.
- Export the outline as both SVG and DXF.

Use a provisional maximum body width of 320 mm, scaled proportionally from the reference silhouette. Use a provisional thickness of 44 mm.

These dimensions must be configurable rather than hard-coded throughout the project.

### 3D modeling

Convert the outline into a manifold mesh.

Model:

- Front and rear surfaces.
- Rounded body perimeter.
- Front edge bevels.
- An approximate forearm contour.
- Rear belly contour, if practical.
- Pickup cavities/positions.
- Bridge and control placements.

The back-view reference may help locate cavities and approximate construction, but do not invent precise neck-joint engineering or internal routing.

Model the pickups and hardware as separate objects so they can be hidden when evaluating the wood figure.

Make the top surface sufficiently smooth for accurate UV mapping.

**Critical requirement: Geometry must be generated once and reused unchanged for every wood candidate and finish.**

Export the final body mesh to OBJ.

### Geometry validation

Save diagnostic images showing:

- The extracted silhouette overlaid on the original illustration.
- The spline compared against the source outline.
- Front orthographic view of the 3D model.
- Perspective view of the body.
- UV layout.

Automatically verify that all renders use identical geometry, scale, camera, and body placement.

## 4. Wood photograph processing

Process each of the eight photographs individually.

The wood in these photographs is unfinished figured maple. Some pieces have already been paired in bookmatched arrangements; others are single boards.

### Photo correction

For each photograph:

1. Detect the wood boundaries.
2. Separate the wood from the concrete background.
3. Correct perspective distortion with a planar homography.
4. Correct camera rotation.
5. Normalize uneven illumination conservatively.
6. Reduce color casts without destroying the grain contrast.
7. Preserve natural knots, spalting, curl, quilting, and figure variation.
8. Remove background pixels from the resulting texture.

Do not use texture synthesis or generative inpainting.

Where the boundary is ambiguous, provide a manually editable crop specification.

### Bookmatching

For existing two-piece bookmatched sets:

- Identify the physical seam.
- Preserve both photographed halves.
- Align the seam to the guitar centerline.
- Correct perspective independently if required.
- Do not replace either photographed half with an artificial mirror.

For single boards:

- Rotate the image so the intended longitudinal grain direction aligns with the guitar's long axis.
- Simulate a bookmatched opening by creating two mirrored halves.
- Keep the mirrored grain continuous at the centerline.
- Clearly label these results as *simulated bookmatches*, not photographs of actual resawn pieces.

Evaluate suitable orientation for each board, including whether the grain direction should be rotated by 90 degrees.

Do not arbitrarily stretch a narrow board into a full guitar top.

Where physical dimensions are unavailable, document the assumptions and treat the result as a visual study, not evidence that the board is large enough to make the top.

### Texture deliverables

For each candidate, save:

- Original crop.
- Perspective-corrected texture.
- Bookmatched texture.
- Grayscale figure/contrast map.
- Optional conservative bump map.
- Metadata recording source filename, transform, seam location, orientation, and simulated versus physical bookmatch status.

Do not remove existing knots or spalting merely to improve visual symmetry.

## 5. UV mapping

Create a fixed UV map for the guitar top.

Requirements:

- The guitar centerline corresponds to the bookmatch seam.
- The two halves remain correctly oriented.
- There is no visible UV stretching or skewing.
- Texture scale remains consistent between candidates.
- Figuring is not artificially enlarged or compressed to fill the body.
- Every candidate uses the same mapping convention.

For each candidate, allow a configurable translation/rotation within the available wood area so we can test how the blank should be positioned before cutting.

Ensure the UV representation respects the actual photographed wood rather than creating synthetic texture detail.

## 6. Finish shader design

The target finish is visually inspired by the supplied **PRS SE Special Semi-Hollow charcoal-black figured-maple finish**.

Pay particular attention to its neutral charcoal coloration, silver-grey grain highlights, deep black shadows, and glossy clearcoat.

This is not a traditional brown or tobacco burst.

Build the material with separate, adjustable components.

### Layer A: Wood albedo and figure

Use the real corrected wood texture.

Derive a conservative figure mask from local contrast, luminance variation, and spatial filtering.

Preserve the different figure characteristics of every candidate.

Do not interpret all dark pixels as physically dye-absorbing grain without qualification. The source photographs contain lighting and surface preparation differences.

### Layer B: Black dye / stain

Approximate a strongly contrasting black-dye-and-sandback finishing process.

Target:

- Near-black grain shadows.
- Neutral charcoal base color.
- Silver-grey figure highlights.
- High grain contrast.
- Minimal warm brown or orange undertones.

Starting color targets:

- Darkest grain: `#08090A`
- Base charcoal: `#18191B`
- Figure highlights: `#64676C`
- Strongest figure highlights: `#888B90`

These are initial artistic targets, not measured PRS material specifications.

Create adjustable parameters:

- Dye intensity.
- Sandback strength.
- Figure contrast.
- Highlight brightness.
- Neutrality/warmth.
- Overall darkness.

Use image texture data and color ramps or equivalent shader logic.

Do not simply place a translucent black rectangle over the original photograph.

### Layer C: Transparent black burst

Build a procedural black burst using UV coordinates or a distance field derived from the actual body perimeter.

**The burst should follow the guitar outline, not simply form a circle or ellipse.**

Requirements:

- Near-black at the outer edge.
- Wide transition extending inward.
- Continuous smooth transparency gradient.
- No abrupt opaque ring.
- Figure remains faintly visible beneath the outer transition where appropriate.
- The center remains charcoal rather than brown.

Initial parameters:

- Burst width: approximately 30–40% of local body half-width.
- Edge opacity: 0.95–1.0.
- Inner opacity: 0.0.
- Smoothstep or smootherstep falloff.
- Adjustable exponent and transition position.

Expose burst width, opacity, falloff, and color independently.

Handle concave cutaways correctly so the burst follows the nearest actual edge.

### Layer D: Gloss clearcoat

Simulate a polished guitar clearcoat using Principled BSDF.

Initial targets:

- Clearcoat weight: high.
- Clearcoat roughness: approximately 0.08–0.15.
- Base roughness: approximately 0.22–0.3.
- IOR: approximately 1.5.

Use reasonable layered-material behavior rather than treating clearcoat highlights as part of the underlying wood texture.

Ensure studio reflections reveal the surface curvature.

### Layer E: Optional figure depth

Add subtle, physically restrained normal/bump variation based on the wood texture.

Avoid making quilted maple appear carved, blistered, or embossed.

Figured maple's chatoyance arises from directional optical effects that cannot be recovered fully from a single photograph. Do not present a generated bump map as a physically exact representation.

Document this limitation.

## 7. Finish presets

Implement at least four presets:

**A. Natural Gloss**

Transparent clearcoat over minimally modified original maple.

**B. Dark Charcoal**

Deep, neutral charcoal stain with visible grain and minimal burst.

**C. PRS-Inspired Charcoal Black Burst**

High-contrast silver-grey figure on very dark charcoal, combined with a wide smooth black burst and deep gloss.

**D. Extreme Black**

Almost-black center, subtle reflected silver figure, and black edges.

Store all parameters in `config/finishes.json`.

Ensure presets are reproducible.

## 8. Studio lighting and cameras

Create a controlled rendering environment.

Use Blender Cycles if available.

Configure:

- Neutral studio background.
- Large softbox key light.
- Subtle fill light.
- Edge/rim illumination.
- Gloss reflections that communicate the clearcoat depth.
- Neutral color management.
- Fixed exposure.

Provide:

1. Front orthographic camera.
2. Three-quarter perspective camera.
3. Figure-detail close-up camera.

The front orthographic view is mandatory for comparison because it prevents perspective differences from confusing the selection.

The same camera settings and lighting must be used for all wood candidates.

Do not change the geometry, camera angle, or exposure to make one piece look more attractive.

## 9. PRS reference calibration

Use the supplied PRS photograph as the visual calibration target.

Compare:

- Overall charcoal darkness.
- Warm/cool balance.
- Relative figure contrast.
- Black-level depth.
- Burst transition width.
- Highlight intensity.
- Clearcoat gloss appearance.

The PRS photograph has its own studio lighting and unknown image processing. Do not assume its raw pixel values correspond directly to material properties.

Tune the finish shader until the *visual impression* is reasonably close under our studio lighting.

Preserve each actual maple blank's unique figure.

Do not introduce PRS-style flame patterns into wood that does not naturally contain them.

## 10. Comparison outputs

Produce a complete comparison grid with all eight candidates.

Every panel must display:

- Source filename.
- Raw bookmatched texture.
- Finished guitar body.
- Finish preset.
- Whether the bookmatch is physical or simulated.

Create comparison grids for Natural Gloss, Dark Charcoal, PRS-Inspired, and Extreme Black.

Also generate one enlarged PRS-Inspired render per piece at a minimum resolution of 1600 × 1600, with consistent framing and no image-generation enhancement.

## 11. Implementation expectations

Use Blender Python (`bpy`) for geometry, materials, scene configuration, and rendering.

Use OpenCV, Pillow, NumPy, or equivalent deterministic image-processing libraries for photo preparation.

Use a configuration-driven pipeline.

All outputs must be reproducible from the original assets.

Provide a command-line interface such as:

```bash
python preprocess.py --input assets/originals
blender -b blender/guitar.blend \
  --python blender/scripts/render.py -- \
  --preset prs_reference --all
```

Exact script names can differ, but document their use.

Use clear, maintainable code and avoid unnecessary dependencies.

Do not use AI image generation, diffusion models, generative fill, hallucinated wood details, or external stock textures.

## 12. Validation and acceptance criteria

The task is complete only when:

- All eight actual photographed maple candidates have been processed.
- All bookmatches are correctly represented or explicitly labeled simulated.
- The 2D guitar outline has been extracted and validated against the supplied reference.
- A real 3D body mesh has been constructed.
- UV coordinates have been assigned.
- Actual wood image textures are used by Blender materials.
- The four finish presets are implemented.
- The PRS-inspired finish has been visually calibrated against the reference.
- All eight candidates have been rendered using identical geometry, lighting, and camera.
- Comparison sheets exist for every finish.
- The `.blend` project opens successfully.
- All render outputs can be reproduced from the supplied assets.

Record and report actual Blender execution, version, render engine, mesh vertex count, and render settings.

Do not claim the renders were produced in Blender unless Blender was actually executed.

If Blender isn't installed, attempt installation using the available environment and permissions. If installation is impossible, clearly report the blocker and do not substitute generated illustrations.

## 13. Execution strategy

Work in these stages:

**Stage 1 — Inspect and preprocess**

Inspect all inputs, identify the eight maple candidates, correct the wood photographs, generate bookmatches, and create a contact sheet.

**Stage 2 — Reconstruct geometry**

Extract and verify the guitar silhouette, generate a 3D body, and export the mesh.

**Stage 3 — Implement material system**

Build the UV map and create the stain, burst, and clearcoat shaders.

**Stage 4 — Reference calibration**

Render two visually different maple candidates (one flamed, one quilted) using the PRS-inspired preset and compare their appearance against the PRS photograph.

**Stage 5 — Batch rendering**

Render all eight candidates under the same conditions.

**Stage 6 — QA and delivery**

Verify repeatability, deliver the editable Blender project, textures, scripts, render grids, and README.

At every stage, execute the code and inspect actual outputs.

Do not stop after Stage 1 or Stage 2 unless an essential input or execution capability is missing.

Make reasonable assumptions where possible, document them, and proceed.

**The project's central principle is simple: the wood textures are real, the geometry is fixed, and the finish is the only thing we are experimenting with.**

