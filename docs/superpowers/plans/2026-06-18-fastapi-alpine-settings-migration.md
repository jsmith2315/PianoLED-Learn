# FastAPI Alpine Settings Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `/settings` to FastAPI + Jinja2 + Alpine, add live LED settings auto-save, immediate LED utility actions, and a grouped live MIDI port apply workflow.

**Architecture:** Reuse the new FastAPI page/API split established by `/songs`, but extend the backend wiring so MIDI input/output ports can be swapped live without restarting the server. Keep `PianoLedRuntime` as the system source of truth and use Alpine only for browser interaction state, auto-save behavior, and action feedback.

**Tech Stack:** Python 3.11, FastAPI, Uvicorn, Jinja2, Alpine.js 2, Tailwind CSS, existing runtime/services, manual Pi smoke testing plus Python compile/startup checks

---

## File Structure

### New files

- `src/piano_led/web/templates/settings.html`
- `src/piano_led/web/static/js/settings-page.js`

### Modified files

- `src/piano_led/app.py`
- `src/piano_led/main.py`
- `src/piano_led/midi/input.py`
- `src/piano_led/midi/output.py`
- `src/piano_led/services/runtime.py`
- `src/piano_led/web/app.py`
- `src/piano_led/web/routes/api.py`
- `src/piano_led/web/routes/pages.py`
- `src/piano_led/web/static/css/app.css`
- `src/piano_led/web/static/css/tailwind.css`
- `src/piano_led/web/templates/base.html`
- `src/piano_led/web/server.py`
- `README.md`
- `docs/architecture/dependencies.md`

## Responsibility Map

- `src/piano_led/app.py`: central backend wiring and live MIDI port reconfiguration helpers
- `src/piano_led/midi/input.py`: input port lifecycle hooks needed for safe live switching
- `src/piano_led/midi/output.py`: output port lifecycle hooks needed for safe live switching
- `src/piano_led/services/runtime.py`: runtime-facing APIs for updating settings and replacing active MIDI backends
- `src/piano_led/web/routes/api.py`: JSON endpoints for settings, MIDI port lists, MIDI apply, and LED utility actions
- `src/piano_led/web/routes/pages.py`: FastAPI HTML route for `/settings`
- `src/piano_led/web/templates/settings.html`: settings control panel markup
- `src/piano_led/web/static/js/settings-page.js`: Alpine 2 page logic for auto-save, utility actions, and grouped MIDI apply
- `src/piano_led/web/server.py`: disable legacy `/settings` page while keeping unmigrated pages on fallback

## Plan Notes

- Keep the Pi workflow stable: `sudo python3 -m piano_led web-serve --host 0.0.0.0 --port 8080 --with-live`
- Do not add a Node runtime dependency requirement to launch the server; only CSS rebuilds require the Tailwind toolchain
- Continue using compile/startup/manual Pi checks rather than introducing a new unit-test push in this slice

### Task 1: Add Live MIDI Reconfiguration Support in the Backend Wiring

**Files:**
- Modify: `src/piano_led/app.py`
- Modify: `src/piano_led/midi/input.py`
- Modify: `src/piano_led/midi/output.py`
- Modify: `src/piano_led/services/runtime.py`

- [ ] **Step 1: Add unsubscribe and replacement-safe input lifecycle support**

Update `src/piano_led/midi/input.py` so input listeners can be detached during a live switch.

Target additions:

```python
class MidiInputPort:
    def subscribe(self, listener): ...

    def unsubscribe(self, listener) -> None:
        self._listeners = [current for current in self._listeners if current is not listener]

    def close(self) -> None:
        return None
```

Keep `MidoMidiInputPort.close()` as the real hardware close path and let fake input inherit the no-op close.

- [ ] **Step 2: Add output lifecycle symmetry where needed**

`src/piano_led/midi/output.py` already has `open()` and `close()` for the real backend. Ensure the fake output also has a stable no-op `close()` so live reconfiguration can treat both backends uniformly.

If needed, add:

```python
class FakeMidiOutputPort(MidiOutputPort):
    def close(self) -> None:
        return None
```

- [ ] **Step 3: Add a reusable backend factory in `app.py`**

Refactor `src/piano_led/app.py` so port creation rules are reusable at startup and at runtime.

Add helpers such as:

```python
def create_midi_input(settings: AppSettings) -> FakeMidiInputPort | MidoMidiInputPort: ...
def create_midi_output(settings: AppSettings) -> FakeMidiOutputPort | MidoMidiOutputPort: ...
```

Reuse those helpers inside `build_application()` so there is only one place that decides fake vs mido behavior.

- [ ] **Step 4: Add runtime-facing replacement methods**

Extend `PianoLedRuntime` in `src/piano_led/services/runtime.py` with explicit lifecycle methods:

```python
def detach_midi_input(self) -> None: ...
def replace_midi_input(self, midi_input: MidiInputPort) -> None: ...
def replace_midi_output(self, midi_output: MidiOutputPort) -> None: ...
```

Rules:

- detach old listener from the current input before swapping
- close old input/output if supported
- attach the new input with `handle_note_event`
- update `self.midi_input`, `self.midi_output`, and `self.playback.midi_output`
- refresh runtime state after a successful swap

- [ ] **Step 5: Add one grouped live MIDI apply helper**

Add an `Application`-level method or helper in `src/piano_led/app.py` that:

- receives desired input and output port names
- clones/updates `settings.midi`
- creates new port objects using the shared factory
- opens them where appropriate
- swaps them into the runtime only after the new ports are ready
- persists settings only on success

Example target:

```python
def apply_midi_ports(application: Application, input_port_name: str, output_port_name: str) -> dict: ...
```

- [ ] **Step 6: Run local compile and startup checks**

Run:

```bash
python3 -m compileall src
python3 -m piano_led status
python3 -m piano_led web-serve --host 127.0.0.1 --port 8080 --seconds 1
```

Expected:

- no syntax errors
- status still works
- server still starts cleanly

- [ ] **Step 7: Commit**

```bash
git add src/piano_led/app.py src/piano_led/midi/input.py src/piano_led/midi/output.py src/piano_led/services/runtime.py src/piano_led/main.py
git commit -m "feat: add live MIDI reconfiguration support"
```

### Task 2: Add Settings and MIDI JSON Endpoints on FastAPI

**Files:**
- Modify: `src/piano_led/web/routes/api.py`
- Modify: `src/piano_led/app.py`
- Modify: `src/piano_led/services/runtime.py`
- Reference: `src/piano_led/config/settings.py`

- [ ] **Step 1: Expose current settings cleanly**

Extend `src/piano_led/web/routes/api.py` with:

- `GET /api/settings`

Return the current `runtime.settings.to_dict()` payload.

- [ ] **Step 2: Keep LED settings update behavior but route it through FastAPI**

Add or retain:

- `POST /api/settings`

Use it to update only the LED-related fields required by the new settings page:

- `note_color`
- `black_key_color`
- `left_hand_note_color`
- `left_hand_black_key_color`
- `right_hand_note_color`
- `right_hand_black_key_color`
- `use_black_key_color`
- `brightness`

Persist through `runtime.settings_store.save(runtime.settings)` and refresh runtime state after success.

- [ ] **Step 3: Add a live MIDI port list endpoint**

Add:

- `GET /api/midi/ports`

Return:

```json
{
  "backend": "mido",
  "input_ports": [...],
  "output_ports": [...],
  "selected_input_port": "...",
  "selected_output_port": "..."
}
```

Use the existing `list_mido_input_ports()` and `list_mido_output_ports()` helpers when the backend is `mido`. For fake backend, return empty lists and the saved selected names.

- [ ] **Step 4: Add the grouped MIDI apply endpoint**

Add:

- `POST /api/midi/apply`

Payload:

```json
{
  "input_port_name": "...",
  "output_port_name": "..."
}
```

Behavior:

- call the new backend helper from Task 1
- return success or a 400 with a clear error message if opening either port fails

- [ ] **Step 5: Add or reuse immediate LED utility endpoints**

Confirm the new `/settings` page can use:

- `POST /api/led/clear`
- `POST /api/led/chase`

If single-step chase is not enough for the desired UI, add a small convenience endpoint for a short fixed chase run. If the current one-step behavior is acceptable, reuse it.

- [ ] **Step 6: Run API startup checks**

Run:

```bash
python3 -m compileall src/piano_led/web src/piano_led/app.py src/piano_led/services/runtime.py
python3 -m piano_led web-serve --host 127.0.0.1 --port 8080 --seconds 1
```

Expected:

- API router imports cleanly
- server startup still succeeds

- [ ] **Step 7: Commit**

```bash
git add src/piano_led/web/routes/api.py src/piano_led/app.py src/piano_led/services/runtime.py
git commit -m "feat: add settings and MIDI FastAPI endpoints"
```

### Task 3: Build the FastAPI + Alpine `/settings` Page

**Files:**
- Create: `src/piano_led/web/templates/settings.html`
- Create: `src/piano_led/web/static/js/settings-page.js`
- Modify: `src/piano_led/web/routes/pages.py`
- Modify: `src/piano_led/web/templates/base.html`
- Modify: `src/piano_led/web/static/css/app.css`
- Modify: `src/piano_led/web/static/css/tailwind.css`

- [ ] **Step 1: Add the `/settings` page route**

Update `src/piano_led/web/routes/pages.py`:

```python
@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"request": request, "page_title": "Settings | Piano LED Learn"},
    )
```

- [ ] **Step 2: Create the settings template**

Create `src/piano_led/web/templates/settings.html` with three sections:

- LED Appearance
- MIDI Ports
- LED Tools

Include:

- color inputs
- black-key toggle
- brightness slider with visible value
- input/output dropdowns
- one `Apply MIDI Ports` button
- `Clear Strip`
- `Run Chase Test`
- status/result cards

Use Alpine 2-compatible markup:

```html
<section x-data="settingsPage()" x-init="init()" x-cloak>
  ...
</section>
```

- [ ] **Step 3: Build the Alpine 2 page component**

Create `src/piano_led/web/static/js/settings-page.js` using the Alpine 2-compatible global function style:

```js
window.settingsPage = function settingsPage() {
  return {
    settings: null,
    midiPorts: { input_ports: [], output_ports: [] },
    selectedInputPort: '',
    selectedOutputPort: '',
    saveTimer: null,
    statusMessage: '',
    statusTone: 'idle',
    isSaving: false,
    async init() { ... },
    queueSettingsSave() { ... },
    async saveLedSettings() { ... },
    async refreshMidiPorts() { ... },
    async applyMidiPorts() { ... },
    async clearStrip() { ... },
    async runChaseTest() { ... },
  };
};
```

Behavior:

- auto-save LED settings with a short debounce
- keep MIDI dropdown changes local until `Apply MIDI Ports`
- update status text and pill state after every action

- [ ] **Step 4: Add page-specific styling polish**

Update `src/piano_led/web/static/css/app.css` so `/settings` matches the visual quality of `/songs`:

- grouped glass cards
- clean form rows
- slider layout
- utility button grouping
- readable status pills

If new Tailwind utility classes appear in the template or JS, rebuild `tailwind.css`.

- [ ] **Step 5: Rebuild CSS and run template/startup checks**

Run:

```bash
npm run build-css
python3 -m compileall src/piano_led/web
python3 -m piano_led web-serve --host 127.0.0.1 --port 8080 --seconds 1
```

Expected:

- CSS rebuild succeeds
- no template syntax errors
- server starts cleanly

- [ ] **Step 6: Commit**

```bash
git add src/piano_led/web/templates/settings.html src/piano_led/web/static/js/settings-page.js src/piano_led/web/routes/pages.py src/piano_led/web/templates/base.html src/piano_led/web/static/css/app.css src/piano_led/web/static/css/tailwind.css
git commit -m "feat: add Alpine settings page on FastAPI"
```

### Task 4: Retire the Legacy `/settings` Page and Preserve Hybrid Fallback

**Files:**
- Modify: `src/piano_led/web/app.py`
- Modify: `src/piano_led/web/server.py`
- Modify: `README.md`
- Modify: `docs/architecture/dependencies.md`

- [ ] **Step 1: Disable legacy `/settings` inside the fallback WSGI app**

Follow the same pattern used for `/songs`.

Update `src/piano_led/web/server.py` so the legacy app can selectively disable its `/settings` page when mounted behind FastAPI.

Example direction:

```python
def create_web_app(runtime: PianoLedRuntime, enable_songs_page: bool = True, enable_settings_page: bool = True):
    ...
    if enable_settings_page and method == "GET" and path == "/settings":
        return _html_response(start_response, SETTINGS_HTML)
```

- [ ] **Step 2: Mount the fallback with new flags**

Update `src/piano_led/web/app.py` so the fallback WSGI app keeps unmigrated pages but does not shadow the new FastAPI `/settings` route.

- [ ] **Step 3: Update README and dependency notes**

Document:

- the `/settings` page is now on FastAPI + Alpine
- MIDI port changes can be applied live from the page
- CSS rebuilds still require the Tailwind toolchain when UI styles change

Also add a short note that Raspberry Pi Bookworm may require:

```bash
python3 -m pip install --break-system-packages -e .
```

and reference `docs/architecture/pi-install-notes.md`.

- [ ] **Step 4: Final local sanity checks**

Run:

```bash
python3 -m compileall src
python3 -m piano_led status
python3 -m piano_led web-serve --host 127.0.0.1 --port 8080 --seconds 1
```

Expected:

- no syntax errors
- no startup errors
- existing hybrid pages still mount correctly

- [ ] **Step 5: Commit**

```bash
git add src/piano_led/web/app.py src/piano_led/web/server.py README.md docs/architecture/dependencies.md
git commit -m "refactor: migrate settings page onto FastAPI"
```

### Task 5: Pi Manual Validation Handoff

**Files:**
- Modify: `README.md` only if the exact Pi steps need clarification after implementation

- [ ] **Step 1: Prepare the Pi validation checklist**

Ask for this exact sequence on the Pi:

```bash
cd ~/PianoLED-Learn
git pull
sudo python3 -m pip install --break-system-packages -e .
sudo python3 -m piano_led web-serve --host 0.0.0.0 --port 8080 --with-live
```

Skip `npm` on the Pi unless CSS changed after the last committed compiled build and Node is available there.

- [ ] **Step 2: Ask for these manual checks**

Have the user verify:

- `/settings` loads and shows all sections
- changing color inputs auto-saves
- brightness changes auto-save
- black-key toggle auto-saves
- `Clear Strip` works immediately
- `Run Chase Test` works immediately
- MIDI input/output dropdowns list the expected ports
- pressing `Apply MIDI Ports` switches both ports live or shows a clear error
- after a successful apply, live note input still works without a server restart

- [ ] **Step 3: Keep branch state clean**

Run:

```bash
git status --short
```

Expected:

- no unintended local changes remain after the implementation commits

## Self-Review

### Spec coverage

- `/settings` on FastAPI + Alpine: covered in Tasks 2 and 3
- LED auto-save controls: covered in Task 3
- grouped MIDI apply workflow: covered in Tasks 1 and 2
- immediate LED utility actions: covered in Tasks 2 and 3
- live MIDI switch without restart: covered in Tasks 1, 2, and 5

### Placeholder scan

- No `TODO` or `TBD` placeholders remain
- Each task names concrete files and verification commands
- The plan follows the repo's real verification workflow rather than introducing unrelated test requirements

### Type and naming consistency

- `/settings` Alpine component name: `settingsPage`
- live MIDI apply endpoint: `POST /api/midi/apply`
- MIDI list endpoint: `GET /api/midi/ports`

