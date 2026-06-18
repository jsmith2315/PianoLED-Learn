# FastAPI Alpine Songs Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current custom WSGI `/songs` page with a FastAPI + Jinja2 + Alpine.js + Tailwind implementation while keeping the rest of the app runnable on the Pi.

**Architecture:** Add a new FastAPI web entry layer that owns page routing, static files, and JSON APIs, while keeping `PianoLedRuntime` as the only source of application truth. Migrate `/songs` first, preserve current runtime/service behavior, and keep the existing `web-serve` command working with the same Pi workflow.

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, Jinja2, Alpine.js, Tailwind CSS, existing `PianoLedRuntime`, manual Pi smoke tests plus Python compile/import sanity checks

---

## File Structure

### New files

- `src/piano_led/web/app.py`
- `src/piano_led/web/routes/__init__.py`
- `src/piano_led/web/routes/pages.py`
- `src/piano_led/web/routes/api.py`
- `src/piano_led/web/templates/base.html`
- `src/piano_led/web/templates/home.html`
- `src/piano_led/web/templates/songs.html`
- `src/piano_led/web/static/css/app.css`
- `src/piano_led/web/static/css/input.css`
- `src/piano_led/web/static/css/tailwind.css`
- `src/piano_led/web/static/js/alpine.min.js`
- `src/piano_led/web/static/js/songs-page.js`
- `package.json`
- `tailwind.config.js`

### Modified files

- `pyproject.toml`
- `src/piano_led/main.py`
- `src/piano_led/web/server.py`
- `docs/architecture/dependencies.md`
- `README.md`

### Responsibility map

- `src/piano_led/web/app.py`: create the FastAPI app, template environment, static mount, and router wiring
- `src/piano_led/web/routes/pages.py`: HTML page routes
- `src/piano_led/web/routes/api.py`: runtime-backed JSON endpoints used by Alpine
- `src/piano_led/web/templates/*.html`: page markup with Jinja layout inheritance
- `src/piano_led/web/static/js/songs-page.js`: Alpine component for `/songs`
- `src/piano_led/web/static/css/*`: Tailwind input, compiled output, and small project-specific polish
- `src/piano_led/main.py`: keep `python3 -m piano_led web-serve` working while switching from WSGI to ASGI
- `src/piano_led/web/server.py`: temporarily remain as the legacy page source until later pages migrate, or become a compatibility wrapper if needed

## Plan Notes

- This plan follows the existing project workflow: no new unit-test push in this slice unless a tiny smoke helper falls out naturally.
- Verification uses `compileall`, import/startup checks, and Pi manual smoke tests after each meaningful change.
- Keep the CLI command shape stable: `python3 -m piano_led web-serve --host 0.0.0.0 --port 8080 --with-live`

### Task 1: Add FastAPI and Tailwind Foundation

**Files:**
- Create: `package.json`
- Create: `tailwind.config.js`
- Create: `src/piano_led/web/static/css/input.css`
- Create: `src/piano_led/web/static/css/app.css`
- Modify: `pyproject.toml`
- Modify: `docs/architecture/dependencies.md`
- Modify: `README.md`

- [ ] **Step 1: Add Python web dependencies to the project metadata**

Update `pyproject.toml` to declare runtime dependencies for the new web layer:

```toml
[project]
name = "piano-led"
version = "0.1.0"
description = "Piano LED visualizer and learning assistant for Raspberry Pi"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115,<1.0",
  "uvicorn>=0.30,<1.0",
  "jinja2>=3.1,<4.0",
]
```

- [ ] **Step 2: Add Tailwind build metadata**

Create `package.json` with a single-purpose build command:

```json
{
  "name": "piano-led-web",
  "private": true,
  "scripts": {
    "build-css": "tailwindcss -i ./src/piano_led/web/static/css/input.css -o ./src/piano_led/web/static/css/tailwind.css --minify"
  },
  "devDependencies": {
    "tailwindcss": "^3.4.17"
  }
}
```

Create `tailwind.config.js`:

```js
module.exports = {
  content: [
    "./src/piano_led/web/templates/**/*.html",
    "./src/piano_led/web/static/js/**/*.js",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
```

- [ ] **Step 3: Add the CSS source files**

Create `src/piano_led/web/static/css/input.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
```

Create `src/piano_led/web/static/css/app.css` with the project-specific layer:

```css
body {
  background: linear-gradient(120deg, #f4efe6, #dfe9f3);
  color: #1f2a37;
}

[x-cloak] {
  display: none !important;
}
```

- [ ] **Step 4: Document dependency and install expectations**

Update `docs/architecture/dependencies.md` to add approved notes for:

- `fastapi`
- `uvicorn`
- `jinja2`
- Tailwind build tooling for the Pi web UI layer

Update `README.md` with the install/build flow:

```bash
python3 -m pip install -e .
npm install
npm run build-css
python3 -m piano_led web-serve --host 0.0.0.0 --port 8080
```

- [ ] **Step 5: Run metadata and build sanity checks**

Run:

```bash
python3 -m compileall src
npm install
npm run build-css
```

Expected:

- Python compile completes without syntax errors
- `tailwind.css` is generated under `src/piano_led/web/static/css/`

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml package.json tailwind.config.js src/piano_led/web/static/css/input.css src/piano_led/web/static/css/app.css docs/architecture/dependencies.md README.md src/piano_led/web/static/css/tailwind.css
git commit -m "build: add FastAPI and Tailwind web foundation"
```

### Task 2: Introduce the FastAPI App Shell

**Files:**
- Create: `src/piano_led/web/app.py`
- Create: `src/piano_led/web/routes/__init__.py`
- Create: `src/piano_led/web/routes/pages.py`
- Create: `src/piano_led/web/templates/base.html`
- Create: `src/piano_led/web/templates/home.html`
- Modify: `src/piano_led/main.py`

- [ ] **Step 1: Create the FastAPI app factory**

Create `src/piano_led/web/app.py` with a factory that accepts `PianoLedRuntime` and builds the app:

```python
"""FastAPI application factory for Piano LED Learn."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from piano_led.web.routes.pages import create_page_router


def create_fastapi_app(runtime):
    web_root = Path(__file__).resolve().parent
    app = FastAPI(title="Piano LED Learn")
    app.mount("/static", StaticFiles(directory=web_root / "static"), name="static")
    app.include_router(create_page_router(runtime))
    return app
```

Use `Path(__file__).parent`-based paths so the static/template lookup does not depend on the current working directory.

- [ ] **Step 2: Create the first page router**

Create `src/piano_led/web/routes/pages.py` with:

```python
"""HTML page routes for the FastAPI web UI."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path


def create_page_router(runtime):
    router = APIRouter()
    templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))

    @router.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return templates.TemplateResponse(
            request,
            "home.html",
            {"request": request, "runtime_summary": runtime.describe()},
        )

    return router
```

- [ ] **Step 3: Add a shared base template and simple home page**

Create `base.html` with:

- nav links for `/`, `/settings`, `/keymap`, `/songs`, `/practice`
- `<link>` tags for `/static/css/tailwind.css` and `/static/css/app.css`
- `<script defer src="/static/js/alpine.min.js"></script>`
- a `{% block content %}` section

Create `home.html` extending `base.html` with a simple card-based landing page.

- [ ] **Step 4: Switch `web-serve` to ASGI**

Modify `src/piano_led/main.py` so `web-serve` uses the FastAPI app instead of `wsgiref.simple_server`.

Target shape:

```python
import uvicorn

from piano_led.web.app import create_fastapi_app

if args.command == "web-serve":
    app = create_fastapi_app(application.runtime)
    uvicorn.run(app, host=args.host, port=args.port)
```

Preserve:

- `--host`
- `--port`
- `--with-live`
- the current live MIDI open behavior before server startup

- [ ] **Step 5: Run startup sanity checks**

Run:

```bash
python3 -m compileall src/piano_led/web src/piano_led/main.py
python3 -m piano_led web-serve --host 127.0.0.1 --port 8080 --seconds 1
```

Expected:

- compile succeeds
- the app starts without route or template errors

- [ ] **Step 6: Commit**

```bash
git add src/piano_led/web/app.py src/piano_led/web/routes/__init__.py src/piano_led/web/routes/pages.py src/piano_led/web/templates/base.html src/piano_led/web/templates/home.html src/piano_led/main.py
git commit -m "feat: add FastAPI app shell for web ui"
```

### Task 3: Move the Songs APIs Behind FastAPI

**Files:**
- Create: `src/piano_led/web/routes/api.py`
- Modify: `src/piano_led/web/app.py`
- Modify: `src/piano_led/main.py`
- Reference: `src/piano_led/services/runtime.py`
- Reference: `src/piano_led/songs/hand_config.py`

- [ ] **Step 1: Create typed JSON API routes for `/songs`**

Create `src/piano_led/web/routes/api.py` with a router factory that exposes:

- `GET /api/songs`
- `GET /api/song-selection`
- `POST /api/song-selection`
- `GET /api/song-hand-config`
- `POST /api/song-hand-config`

Use the runtime methods that already exist:

```python
runtime.list_songs()
runtime.get_song_selection_state()
runtime.select_song(relative_path)
runtime.get_song_hand_config_state(relative_path)
runtime.save_song_hand_config(
    relative_path,
    left_hand_tracks,
    right_hand_tracks,
    left_hand_channels,
    right_hand_channels,
)
```

- [ ] **Step 2: Preserve current request validation behavior**

Handle invalid payloads with explicit 400 responses instead of silent fallthrough:

```python
from fastapi import HTTPException

if not relative_path:
    raise HTTPException(status_code=400, detail="relative_path is required")
```

Mirror current behavior for invalid note/track/channel values so the browser keeps getting predictable JSON errors.

- [ ] **Step 3: Wire the API router into the app**

Update `src/piano_led/web/app.py`:

```python
from piano_led.web.routes.api import create_api_router

app.include_router(create_api_router(runtime))
```

- [ ] **Step 4: Keep the command surface unchanged**

Re-run the CLI path that the Pi uses:

```bash
python3 -m piano_led status
python3 -m piano_led web-serve --host 127.0.0.1 --port 8080 --seconds 1
```

Expected:

- `status` still prints the runtime summary
- `web-serve` starts with the new app and exits cleanly after the bounded run

- [ ] **Step 5: Commit**

```bash
git add src/piano_led/web/routes/api.py src/piano_led/web/app.py src/piano_led/main.py
git commit -m "feat: move songs runtime endpoints to FastAPI"
```

### Task 4: Build the Alpine-Driven `/songs` Page

**Files:**
- Create: `src/piano_led/web/templates/songs.html`
- Create: `src/piano_led/web/static/js/songs-page.js`
- Create: `src/piano_led/web/static/js/alpine.min.js`
- Modify: `src/piano_led/web/routes/pages.py`
- Modify: `src/piano_led/web/static/css/app.css`

- [ ] **Step 1: Add the `/songs` page route**

Update `src/piano_led/web/routes/pages.py`:

```python
@router.get("/songs", response_class=HTMLResponse)
def songs(request: Request):
    return templates.TemplateResponse(
        request,
        "songs.html",
        {"request": request},
    )
```

Do not inject large JSON blobs into the template. Let Alpine load data from the JSON APIs.

- [ ] **Step 2: Create the Jinja template for the songs page**

Create `src/piano_led/web/templates/songs.html` extending `base.html`.

The page needs:

- a song selector card
- a save selected song button
- a hand setup card
- four checkbox groups:
  - left tracks
  - right tracks
  - left channels
  - right channels
- a status area for API responses
- a summary panel showing saved backend state

Use Alpine bindings instead of manual `document.createElement()` rendering:

```html
<section x-data="songsPage()" x-init="init()" x-cloak>
  <select x-model="selectedSongPath">
    <template x-for="song in songs" :key="song.relative_path">
      <option :value="song.relative_path" x-text="song.display_title"></option>
    </template>
  </select>
  <template x-for="track in handSummary.track_indices" :key="'lt-' + track">
    <label>
      <input type="checkbox" :value="track" x-model="localConfig.left_hand_tracks">
      <span x-text="track"></span>
    </label>
  </template>
</section>
```

- [ ] **Step 3: Implement the Alpine component**

Create `src/piano_led/web/static/js/songs-page.js` with a single Alpine component:

```js
document.addEventListener('alpine:init', () => {
  Alpine.data('songsPage', () => ({
    songs: [],
    selectedSongPath: '',
    savedSongPath: '',
    localConfig: {
      left_hand_tracks: [],
      right_hand_tracks: [],
      left_hand_channels: [],
      right_hand_channels: [],
    },
    savedConfig: null,
    handSummary: { track_indices: [], channels: [] },
    statusMessage: '',
    isLoading: false,
    async init() {
      await this.refreshSongs();
      await this.refreshHandSetup();
      window.setInterval(() => {
        this.refreshSongs();
        this.refreshHandSetup();
      }, 1000);
    },
    async refreshSongs() {},
    async refreshHandSetup() {},
    async saveSongSelection() {},
    async saveHandSetup() {},
    get isSongDirty() { return this.selectedSongPath !== this.savedSongPath; },
    get isHandSetupDirty() {
      return JSON.stringify(this.localConfig) !== JSON.stringify(this.savedConfig);
    },
  }));
});
```

Core rule:

- background refresh may update summaries and saved state
- background refresh must not overwrite unsaved local checkbox selections

- [ ] **Step 4: Vendor Alpine and polish the page styling**

Add `alpine.min.js` as a checked-in static asset.

Update `app.css` with:

- card spacing
- status pill styles
- disabled button states
- checkbox-grid spacing
- readable mobile layout

- [ ] **Step 5: Build CSS and run browser startup checks**

Run:

```bash
npm run build-css
python3 -m compileall src/piano_led/web
python3 -m piano_led web-serve --host 127.0.0.1 --port 8080 --seconds 1
```

Expected:

- CSS rebuild succeeds
- Python compile succeeds
- `/songs` can render without template or static asset errors

- [ ] **Step 6: Commit**

```bash
git add src/piano_led/web/templates/songs.html src/piano_led/web/static/js/songs-page.js src/piano_led/web/static/js/alpine.min.js src/piano_led/web/routes/pages.py src/piano_led/web/static/css/app.css src/piano_led/web/static/css/tailwind.css
git commit -m "feat: add Alpine songs page on FastAPI"
```

### Task 5: Preserve Pi Workflow and Manual Validation

**Files:**
- Modify: `README.md`
- Modify: `src/piano_led/main.py`
- Modify: `deploy/install-pi-service.sh` only if needed for launch command parity

- [ ] **Step 1: Make sure the Pi command path stays familiar**

Confirm `src/piano_led/main.py` still supports:

```bash
python3 -m piano_led web-serve --host 0.0.0.0 --port 8080 --with-live
```

If `uvicorn.run()` blocks the current bounded `--seconds` behavior, either:

- keep `--seconds` only as a development convenience with documented limitation, or
- wrap `uvicorn.Server` directly so bounded runs still work

Pick one approach and document it explicitly in `README.md`.

- [ ] **Step 2: Update run and build instructions**

Add a short Pi-specific section to `README.md`:

```bash
git pull
python3 -m pip install -e .
npm install
npm run build-css
sudo python3 -m piano_led web-serve --host 0.0.0.0 --port 8080 --with-live
```

Also note that future CSS-only changes still need `npm run build-css` before launching.

- [ ] **Step 3: Perform local sanity checks before handing off to the Pi**

Run:

```bash
python3 -m compileall src
python3 -m piano_led status
python3 -m piano_led web-serve --host 127.0.0.1 --port 8080 --seconds 1
```

Expected:

- compile succeeds
- status succeeds
- server starts cleanly

- [ ] **Step 4: Hand off Pi smoke tests**

Ask for this exact Pi test sequence:

```bash
cd ~/PianoLED-Learn
git pull
python3 -m pip install -e .
npm install
npm run build-css
sudo python3 -m piano_led web-serve --host 0.0.0.0 --port 8080 --with-live
```

Then manually verify:

- `/songs` opens
- selecting a song stays selected locally
- saving selected song persists the selection
- left/right hand checkboxes stay checked while idle
- saving hand setup persists the config
- refreshing the page reloads the saved config correctly

- [ ] **Step 5: Commit**

```bash
git add README.md src/piano_led/main.py deploy/install-pi-service.sh
git commit -m "docs: preserve Pi workflow for FastAPI songs migration"
```

### Task 6: Retire the Inline `/songs` Implementation Without Breaking Future Pages

**Files:**
- Modify: `src/piano_led/web/server.py`
- Modify: `src/piano_led/web/routes/pages.py`
- Modify: `src/piano_led/web/routes/api.py`

- [ ] **Step 1: Remove duplicated `/songs` page behavior from the legacy module**

Once the FastAPI `/songs` page is live and verified, simplify `src/piano_led/web/server.py` so it no longer carries a second `/songs` page implementation.

Two acceptable end states:

```python
"""Legacy inline web UI kept temporarily for non-migrated pages."""
```

or

```python
"""Compatibility helpers for remaining pre-template pages."""
```

Do not leave two active `/songs` implementations that can drift apart.

- [ ] **Step 2: Keep future migration boundaries obvious**

Add or update module docstrings so the next worker can tell:

- which routes are already on FastAPI + templates
- which pages still live in the legacy inline layer
- which module should be migrated next

- [ ] **Step 3: Final sanity run**

Run:

```bash
python3 -m compileall src
python3 -m piano_led status
python3 -m piano_led web-serve --host 127.0.0.1 --port 8080 --seconds 1
```

Expected:

- no syntax errors
- no import errors
- no duplicate-route startup failures

- [ ] **Step 4: Commit**

```bash
git add src/piano_led/web/server.py src/piano_led/web/routes/pages.py src/piano_led/web/routes/api.py
git commit -m "refactor: retire inline songs page after FastAPI migration"
```

## Self-Review

### Spec coverage

- Chosen stack: covered in Tasks 1 and 2
- `/songs` as the first migration slice: covered in Tasks 3 and 4
- Hybrid migration boundary: covered in Tasks 2 and 6
- Pi workflow preservation: covered in Task 5
- Cleaner but not full redesign: covered in Task 4

### Placeholder scan

- No `TODO` or `TBD` placeholders remain
- Each task names exact files and verification commands
- The plan intentionally uses compile/startup/Pi smoke checks instead of adding unit-test work that the project workflow does not want in this slice

### Type and naming consistency

- FastAPI app factory name: `create_fastapi_app`
- page router factory name: `create_page_router`
- API router factory name: `create_api_router`
- Alpine component name: `songsPage`
