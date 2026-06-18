# FastAPI + Alpine Songs Migration Design

## Summary

Move the project web layer toward `FastAPI + Jinja2 + Alpine.js + Tailwind` by migrating the `/songs` page first. This gives the project a cleaner long-term web foundation while fixing the class of UI state bugs where checkboxes and dropdowns revert during background refreshes.

This migration is intentionally incremental. The runtime, MIDI handling, playback engine, keymap logic, and calibration logic remain the source of truth and are not redesigned as part of this slice.

## Goals

- Replace the current custom inline-HTML page pattern with a clearer web structure.
- Use Alpine.js to manage browser-local interaction state on the `/songs` page.
- Keep saved application state in the backend runtime.
- Improve the visual polish of `/songs` without requiring a full app redesign.
- Establish a reusable pattern for later migration of `/settings`, `/keymap`, and `/practice`.

## Non-Goals

- Redesign the playback engine.
- Redesign the whole site visually in one pass.
- Rewrite every page in one migration.
- Move runtime business logic into frontend JavaScript.

## Chosen Stack

### Backend

Use FastAPI as the primary web framework.

Why FastAPI:

- It fits the project's Python-first architecture.
- It works well with Python 3.11.
- It gives a clean route structure for HTML pages and JSON APIs.
- It supports Jinja2 templates, static files, and later WebSockets if needed.
- It is a better long-term foundation than continuing to expand a custom WSGI file.

### Templates

Use Jinja2 templates for server-rendered HTML.

Why Jinja2:

- It keeps page structure readable.
- It avoids embedding large HTML strings inside Python modules.
- It works naturally with shared layouts and reusable sections.
- It keeps the initial migration simpler than introducing a full frontend SPA.

### Frontend Behavior

Use Alpine.js for page-local reactivity.

Why Alpine:

- It is lightweight enough for a Pi-hosted control surface.
- It handles checkboxes, dropdowns, dirty state, loading flags, and conditional sections well.
- It reduces the amount of manual DOM update code.
- It maps well to the old project's successful lightweight frontend approach.

### Styling

Use Tailwind CSS with a small build step on the Pi.

Why Tailwind:

- It gives cleaner reusable styling than continuing with ad hoc inline CSS.
- It supports quick iteration toward a more polished interface.
- It matches the stronger parts of the old project's UI stack.
- The build step stays isolated to styling and does not affect runtime MIDI or LED logic.

## Architecture

### Runtime Boundary

`services/runtime.py` remains the system source of truth for application behavior.

The web layer is responsible for:

- rendering pages
- accepting browser requests
- calling runtime methods
- returning HTML or JSON responses

The web layer is not responsible for:

- MIDI routing decisions
- playback scheduling
- hand assignment business rules
- LED rendering decisions
- keymap persistence rules beyond calling runtime methods

### State Ownership

The migration adopts a strict split between temporary browser state and saved backend state.

Browser-owned temporary state:

- currently highlighted song in the dropdown
- checkbox state before save
- loading indicators
- dirty-state tracking
- inline error and success messages

Backend-owned saved state:

- selected song
- persisted hand track/channel configuration
- runtime playback and MIDI state
- song library metadata

This split is the key design rule that prevents the existing "selection snaps back" and "checkbox unticks itself" problems.

## File Structure

The new web structure should be introduced under the existing web package:

- `src/piano_led/web/app.py`
- `src/piano_led/web/routes/pages.py`
- `src/piano_led/web/routes/api.py`
- `src/piano_led/web/templates/base.html`
- `src/piano_led/web/templates/home.html`
- `src/piano_led/web/templates/songs.html`
- `src/piano_led/web/static/css/tailwind.css`
- `src/piano_led/web/static/css/app.css`
- `src/piano_led/web/static/js/alpine.min.js`
- `src/piano_led/web/static/js/songs-page.js`

### Responsibilities

`app.py`

- create the FastAPI app
- mount static assets
- include page and API routers
- provide any startup wiring needed for the current runtime object

`routes/pages.py`

- define page routes
- return Jinja-rendered templates
- keep HTML-serving concerns separate from JSON APIs

`routes/api.py`

- define JSON endpoints used by Alpine
- preserve the current runtime-backed API behavior
- keep request parsing and response shaping together

`base.html`

- hold shared page layout
- include navigation
- load Alpine and shared styles
- provide a consistent shell for future pages

`songs.html`

- provide the first Alpine-powered page
- render the song selector and hand setup UI
- keep markup declarative and readable

`songs-page.js`

- hold the Alpine component for the `/songs` page
- manage local page state, fetches, save flows, dirty tracking, and refresh behavior

`tailwind.css`

- contain the compiled Tailwind output served by FastAPI

`app.css`

- contain a small amount of project-specific styling that does not belong in utility classes

## First Migration Slice: `/songs`

The first migration slice fully converts `/songs` and leaves other pages simple until later.

### `/songs` Responsibilities

The Alpine-driven `/songs` page should manage:

- song list loading
- current dropdown value
- selected song save action
- hand track checkbox groups
- hand channel checkbox groups
- dirty-state tracking
- disabled/enabled save buttons
- status messaging for success and error states

### Behavioral Rules

- Changing the dropdown updates local browser state immediately.
- Background refresh must not overwrite unsaved local state.
- Saving selected song updates persisted runtime state.
- Saving hand setup updates persisted runtime state.
- Refreshes may update backend-derived summaries, but must not clobber local unsaved edits.
- The page should clearly show the difference between saved state and in-progress changes.

## Migration Strategy

Use a hybrid migration instead of a full switch all at once.

### Hybrid Phase

- Keep the existing runtime and service layer unchanged.
- Move JSON APIs behind FastAPI.
- Add Jinja-rendered pages.
- Convert `/songs` first.
- Keep the remaining pages simple and migrate them one at a time afterward.

### Why Hybrid

- It keeps the app runnable on the Pi throughout the migration.
- It limits risk to one page.
- It creates a reusable pattern before touching more complex screens.
- It avoids mixing frontend and runtime rewrites into a single change.

## Visual Direction

The first `/songs` page should land between the current bare-bones look and the old project's fuller polish.

That means:

- cleaner visual hierarchy
- better spacing and grouping
- clearer action buttons and status states
- improved form readability

It does not mean:

- reproducing the old project pixel-for-pixel
- introducing a full design system before the structure is stable

## Testing and Validation

This project is validated primarily on the Pi through manual smoke testing after each change.

For this migration, success means:

- `python3 -m piano_led web-serve` still starts cleanly on the Pi
- the `/songs` page is served through FastAPI
- Alpine manages the `/songs` form state
- the song dropdown does not revert unexpectedly
- left and right hand track/channel checkboxes do not untick themselves during refreshes
- saving song selection still updates runtime state correctly
- saving hand setup still updates runtime state correctly
- the page looks cleaner than the current version without a full site redesign
- the structure is reusable for later migration of `/settings`, `/keymap`, and `/practice`

## Compatibility Constraints

The chosen stack must remain practical for the target environment:

- Raspberry Pi Zero 2 W
- Raspberry Pi OS 32-bit Lite Bookworm
- Python 3.11

The design assumes:

- FastAPI is installed in the project environment
- Jinja2 is installed in the project environment
- Alpine.js is shipped as a static asset
- Tailwind CSS is built into static CSS assets before runtime use

## Follow-On Work

After this design is approved and implemented, the same pattern should be reused for:

- `/keymap`
- `/settings`
- `/practice`

The playback, learning, and score pages should continue to build on the same principle:

- backend runtime owns application truth
- Alpine owns short-lived browser interaction state
- templates keep page structure readable

