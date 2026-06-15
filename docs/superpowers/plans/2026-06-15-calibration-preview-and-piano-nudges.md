# Calibration Preview And Piano Nudges Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add whole-keyboard preview tools and more intuitive piano-key calibration nudges so the keymap can be aligned quickly before fine tuning.

**Architecture:** Extend the runtime with a small set of preview-mode flags and rendering helpers instead of introducing a separate calibration engine. Keep the web layer thin by exposing new runtime actions over the existing `/keymap` page and API endpoints, with tests covering both runtime behavior and browser-visible controls.

**Tech Stack:** Python 3.11, `unittest`, existing WSGI web UI, existing fake LED driver and runtime services.

---

### Task 1: Define runtime tests for preview and piano-note nudges

**Files:**
- Modify: `tests/services/test_runtime.py`
- Test: `tests/services/test_runtime.py`

- [ ] **Step 1: Write the failing tests**

Add tests for:
- previewing the whole keymap with black/white key colors
- shifting the whole keymap left/right as one block
- restoring full-keyboard preview after confirming a calibration note
- nudging a selected note left/right by pressing any lower/higher piano key

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.services.test_runtime -v`
Expected: FAIL with missing runtime methods or mismatched preview behavior.

- [ ] **Step 3: Write minimal implementation**

Implement runtime helpers and note-handling updates only as needed to satisfy the tests.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.services.test_runtime -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -- tests/services/test_runtime.py src/piano_led/services/runtime.py
git commit -m "feat: add runtime support for keymap preview and piano nudges"
```

### Task 2: Add browser/API coverage for whole-map preview controls

**Files:**
- Modify: `tests/web/test_server.py`
- Test: `tests/web/test_server.py`

- [ ] **Step 1: Write the failing tests**

Add tests that `/keymap` includes:
- preview whole map controls
- whole-map shift controls
- a calibration full-keyboard preview toggle

Add API tests for:
- previewing the full map
- shifting the full map
- toggling/showing the calibration full-preview mode

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.web.test_server -v`
Expected: FAIL because the controls and endpoints do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Implement the new `/api/keymap/*` and `/api/calibration/*` actions in the web server only after the tests fail.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.web.test_server -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -- tests/web/test_server.py src/piano_led/web/server.py
git commit -m "feat: add keymap preview and calibration preview controls"
```

### Task 3: Update docs and verify the full suite

**Files:**
- Modify: `docs/stages/stage-03-calibration-workflow.md`
- Modify: `docs/stages/stage-04-tablet-web-ui-foundation.md`
- Test: `tests/services/test_runtime.py`
- Test: `tests/web/test_server.py`

- [ ] **Step 1: Update the stage docs**

Document the new flow:
- generate keymap
- preview full map
- shift whole map left/right
- optionally show full keyboard during calibration
- press lower/higher notes to nudge the selected mapping one step

- [ ] **Step 2: Run the full test suite**

Run: `python -m unittest discover -s tests -t . -v`
Expected: PASS with no regressions.

- [ ] **Step 3: Commit**

```bash
git add -- docs/stages/stage-03-calibration-workflow.md docs/stages/stage-04-tablet-web-ui-foundation.md
git commit -m "docs: describe keymap preview and piano-nudge calibration flow"
```
