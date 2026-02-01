# TODO / Roadmap

## Refactor (post-clean session)
- [ ] Evaluate global coordinator (single fetch, per-entry filtering) vs URL cache.
- [ ] If global coordinator:
  - [ ] Centralize ID fetch + geojson fetch.
  - [ ] Expose per-entry filtered data to entities.
  - [ ] Ensure no regression for multi-instance and unique_id.
- [ ] If shared cache:
  - [ ] Implement shared URL cache with TTL in `hass.data`.
  - [ ] Deduplicate identical API calls across entries.
- [ ] Add/update tests (or manual test checklist).
- [ ] Re-run hassfest after refactor.

## Open Questions
- [ ] Best TTL for cache (2–5 min?) without staleness issues.
- [ ] Whether to keep config-flow coordinate validation (depends on user feedback).

