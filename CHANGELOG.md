# Changelog

All notable changes to ArgoPilot are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

## [v1.1.0] - 2026-11-24

### Added
- `GET /v1/farms/{id}/summary` — returns `plot_count` and `total_area_m2` for a farm.
  An empty farm returns zero for both. An unknown farm returns `404 NOT_FOUND`.
