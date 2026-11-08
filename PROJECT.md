# Comfy3D project plan

## Direction

Comfy3D is maintained for compatibility and reproducible Docker-based ComfyUI
installation, not a new-feature roadmap. It is not retired. New product
development belongs to Remesher, a separate project.

The maintainer's direction is that native 3D alternatives reduce the need for
this environment. This is a scope decision, not a comparative benchmark or a
claim that every existing workflow has a native replacement.

## Maintenance scope

- Preserve the documented Docker installation path and address bounded
  compatibility, dependency, and setup-documentation issues as needed.
- Keep architecture-specific requirements and limitations explicit; a static
  configuration check is not proof of a working image or GPU workflow.
- Retain reproducible installation as an option for a possible future course.
  Course use is conditional: no teaching commitment, schedule, or curriculum is
  established by this plan. Validate the chosen image and workflow before use.

Existing open or draft pull requests are proposals, not new-feature commitments
under this plan. Each requires a separate scope decision and normal review.

## Installation and verification

Use the existing [README setup instructions](README.md), including prerequisites,
local development, the published AMD64 image, and the native ARM64 / DGX Spark
build with its ONNX Runtime limitation. The corresponding configurations are
[docker-compose.yml](docker-compose.yml),
[docker-compose.dev.yml](docker-compose.dev.yml), and
[docker-compose.arm64.yml](docker-compose.arm64.yml).

Maintenance changes should follow the repository's applicable checks and review.
Changes affecting a runtime require evidence for the affected architecture and
workflow; publishing this document does not certify a new image, deployment, or
inference result.
