# Changelog

All notable changes to ArgoPilot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

## [v1.2.0] - 2026-11-24

### Added
- `/manage` page in the frontend: forms that register a farm, and a plot with its
  crop, soil and emitter chosen from the registry catalogues. The registry has
  accepted writes since v1.0.0, but nothing outside `curl` could reach them.
- Validation and conflict messages from the registry (`422`, `409`) are shown on
  the form, so a rejected planting date or a duplicate plot name says which field
  to correct. Read paths keep their generic messages.

### Notes
- Forms submit through Next.js Server Actions. The browser still calls no service
  directly.

## [v1.1.0] - 2026-11-24

### Added
- `GET /v1/farms/{id}/summary` — returns `plot_count` and `total_area_m2` for a farm.
  An empty farm returns zero for both. An unknown farm returns `404 NOT_FOUND`.
