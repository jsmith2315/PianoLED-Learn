# FastAPI + Alpine Settings Migration Design

## Summary

Migrate the `/settings` page to the new `FastAPI + Jinja2 + Alpine.js + Tailwind` web stack. This page will become a live control panel for LED appearance settings, MIDI port management, and simple LED utility actions.

This migration follows the same hybrid approach used for `/songs`: move one page at a time while keeping the runtime and the remaining legacy pages working.

## Goals

- Move `/settings` onto the new FastAPI template-based web layer.
- Reuse the Alpine page pattern established by `/songs`.
- Auto-save LED appearance settings when changed.
- Add a grouped MIDI port apply workflow with one explicit action button.
- Keep immediate LED tools available on the same page.

## Non-Goals

- Redesign every settings-related screen in the project.
- Change playback engine behavior.
- Move keymap or calibration workflows into `/settings`.
- Require a server restart for successful MIDI port changes.

## Scope

The migrated `/settings` page should include three main sections.

### LED Appearance

- note color
- black key color
- left hand color
- left hand black key color
- right hand color
- right hand black key color
- black key color toggle
- brightness slider

### MIDI Ports

- MIDI input port dropdown
- MIDI output port dropdown
- one `Apply MIDI Ports` button
- visible connection status/result message

### LED Tools

- `Clear Strip`
- `Run Chase Test`

## Chosen Interaction Model

The page should use two different interaction styles depending on risk and user expectation.

### Auto-Save Controls

LED appearance settings should auto-save:

- colors
- black-key toggle
- brightness

These are lightweight settings and should behave like a live control panel rather than a form the user has to submit manually.

### Explicit Action Controls

The following actions should require an explicit button press:

- `Apply MIDI Ports`
- `Clear Strip`
- `Run Chase Test`

These operations either change live device connections or trigger immediate visible behavior, so they should remain explicit.

## Architecture

### Runtime Boundary

The runtime remains the source of truth for the actual system behavior.

The web layer is responsible for:

- rendering the page
- reading current settings and available port lists
- sending update requests to runtime-backed APIs
- showing success and failure messages

The web layer is not responsible for:

- opening MIDI ports directly
- managing note subscriptions
- deciding how LED rendering works
- persisting settings outside runtime-backed APIs

### New Backend Capability

The current app wiring creates MIDI input/output ports only at startup. To support `/settings`, the backend needs a reusable way to reconfigure MIDI ports while the app is running.

That live reconfiguration path should:

- validate the requested input and output port names
- create replacement MIDI backend objects using the same backend rules used at startup
- reattach the new input to the runtime
- replace the current output object used for playback and assisted output
- update persisted settings only after the live switch succeeds
- return a clear success or error payload

This logic should live in the Python backend/runtime wiring layer, not in the Alpine page.

## API Shape

The migrated page should rely on a small, explicit set of runtime-backed endpoints.

### `GET /api/settings`

Returns:

- current LED settings
- current MIDI backend/port names
- any useful current-state metadata already available

### `POST /api/settings`

Updates and persists LED settings.

Used for:

- colors
- black-key toggle
- brightness

This endpoint should continue to update runtime settings immediately after successful saves.

### `GET /api/midi/ports`

Returns the currently available MIDI input and output ports.

This lets the page populate dropdowns from the live system rather than relying on hardcoded assumptions.

### `POST /api/midi/apply`

Applies both selected MIDI ports together.

Request payload:

- input port name
- output port name

Behavior:

- try to switch both ports live
- return success/failure with clear error text
- update saved settings only on success

### Existing Utility Endpoints

The page can continue using immediate LED utility actions via runtime-backed endpoints such as:

- clear strip
- chase step / chase test

If needed, a small convenience endpoint can be added for a short fixed chase test rather than requiring repeated one-step calls from the browser.

## Alpine Page Behavior

The `/settings` page should manage:

- current LED control values
- current MIDI dropdown values
- loading state
- save/apply status messages
- debounced auto-save for LED settings

### LED Auto-Save Behavior

- changing a color input queues a save shortly after change
- moving the brightness slider updates the visible value immediately and saves after a short debounce
- toggling black-key mode saves immediately or near-immediately

The debounce should be short enough to feel live, but not so aggressive that the page fires a request for every tiny slider movement.

### MIDI Port Behavior

- dropdown changes update local browser state only
- the live runtime does not change until `Apply MIDI Ports` is pressed
- apply result is shown clearly
- on success, saved/current port state updates to match the newly connected ports

### Utility Action Behavior

- `Clear Strip` acts immediately
- `Run Chase Test` acts immediately
- both show clear success or error feedback

## Visual Direction

The `/settings` page should follow the newer polished style introduced for `/songs`:

- grouped cards
- clearer hierarchy
- readable mobile spacing
- obvious status indicators

It should still feel like part of the same app as `/songs`, not like a separate admin console.

## Testing and Validation

This project continues to rely primarily on Pi-based manual validation after each feature slice.

Success means:

- `/settings` is served through the FastAPI + Jinja2 + Alpine stack
- LED appearance controls are visible and usable
- LED appearance settings auto-save correctly
- `Clear Strip` works immediately
- `Run Chase Test` works immediately
- MIDI input/output dropdowns show live available ports
- `Apply MIDI Ports` switches both ports live when valid
- invalid MIDI selections return a clear on-page error
- after a successful apply, the running system uses the new ports without restart
- the page structure is reusable for future settings/config work

## Follow-On Reuse

This migration should establish the reusable pattern for:

- Alpine auto-save control groups
- grouped explicit action buttons
- runtime-backed live device reconfiguration

That pattern can later support:

- richer playback settings
- per-profile hardware settings
- service/runtime diagnostics

