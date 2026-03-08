# AGENTS.md

## Must-follow constraints
- **UI Updates:** Changes to HTML, CSS, or JS in `ide_yonetici.py` (inside `ARAYUZ_HTML`) **must** be followed by a full process restart to reflect.
- **Draft Guard:** Never call `taslakKaydet` during or after `modalKapat`. Saving must only occur during active `input` events to prevent empty-form overwrites.
- **Modal Closure:** Maintain the `mousedown` + `click` dual-check on overlays to prevent accidental closure during text selection drags.
- **Zero Ext. Deps:** Only use Python standard libraries. Adding `pip` requirements is forbidden.

## Validation before finishing
- **Backend:** Successfully execute `python PROJE_TEST_SUITE.py`.
- **Diagnostics:** Verify `GET /api/diagnostic` returns `"Healthy"`.

## Important locations
- **Single File:** Entire app (server + UI) resides in `ide_yonetici.py`.
- **DB Path:** `ide_yonetici.db` is pinned relative to the script's absolute path.

## Change safety rules
- **Migrations:** Wrap `ALTER TABLE` in `try-except` within `tablolari_olustur` for non-breaking schema updates.
- **Draft Persistence (V6):** Preserve the 300ms debounce and "ID is null" guard to prevent draft-production conflicts.

## Known gotchas
- **Browser Cache:** UI changes often require `Ctrl+F5` after server restarts.
- **Auto-Port:** Server increments from `8700` if busy; ensure API calls resolve the dynamic port.
