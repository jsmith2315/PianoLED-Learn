window.settingsPage = function settingsPage() {
  return {
    settings: {
      led: {
        note_color: '#00b894',
        black_key_color: '#0984e3',
        use_black_key_color: true,
        left_hand_note_color: '#00b894',
        left_hand_black_key_color: '#0984e3',
        right_hand_note_color: '#e17055',
        right_hand_black_key_color: '#d63031',
        brightness: 128,
      },
      midi: {
        backend: 'fake',
        input_port_name: '',
        output_port_name: '',
      },
    },
    runtimeState: null,
    midiPorts: {
      input_ports: [],
      output_ports: [],
      selected_input_port: '',
      selected_output_port: '',
      error: '',
    },
    draftMidi: {
      input_port_name: '',
      output_port_name: '',
    },
    brightnessPreview: 128,
    statusMessage: '',
    statusTone: 'idle',
    isLoading: false,
    midiSelectFocused: false,
    pollHandle: null,
    async init() {
      await this.refreshAll();
      this.pollHandle = window.setInterval(async () => {
        if (!this.midiSelectFocused) {
          await this.refreshRuntimeState();
        }
      }, 1000);
    },
    async fetchJson(url, options) {
      const response = await fetch(url, { cache: 'no-store', ...(options || {}) });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || payload.error || 'Request failed.');
      }
      return payload;
    },
    setStatus(message, tone) {
      this.statusMessage = message;
      this.statusTone = tone || 'idle';
    },
    async refreshAll() {
      await this.refreshSettings();
      await this.refreshMidiPorts();
      await this.refreshRuntimeState();
    },
    async refreshSettings() {
      try {
        const payload = await this.fetchJson('/api/settings');
        this.settings = payload;
        this.brightnessPreview = payload.led.brightness;
      } catch (error) {
        this.setStatus(error.message, 'error');
      }
    },
    async refreshMidiPorts() {
      try {
        const payload = await this.fetchJson('/api/midi/ports');
        this.midiPorts = payload;
        this.draftMidi = {
          input_port_name: payload.selected_input_port || '',
          output_port_name: payload.selected_output_port || '',
        };
      } catch (error) {
        this.setStatus(error.message, 'error');
      }
    },
    async refreshRuntimeState() {
      try {
        this.runtimeState = await this.fetchJson('/api/state');
      } catch (error) {
        this.setStatus(error.message, 'error');
      }
    },
    async saveLedSettings() {
      this.isLoading = true;
      try {
        const payload = await this.fetchJson('/api/settings/led', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ led: this.settings.led }),
        });
        this.settings = payload;
        this.brightnessPreview = payload.led.brightness;
        this.setStatus('LED settings saved.', 'success');
        await this.refreshRuntimeState();
      } catch (error) {
        this.setStatus(error.message, 'error');
      } finally {
        this.isLoading = false;
      }
    },
    async applyMidiPorts() {
      this.isLoading = true;
      try {
        const payload = await this.fetchJson('/api/midi/apply', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.draftMidi),
        });
        this.settings.midi.backend = payload.midi_backend;
        this.settings.midi.input_port_name = payload.input_port_name;
        this.settings.midi.output_port_name = payload.output_port_name;
        this.setStatus('MIDI ports applied live.', 'success');
        await this.refreshMidiPorts();
        await this.refreshRuntimeState();
      } catch (error) {
        this.setStatus(error.message, 'error');
      } finally {
        this.isLoading = false;
      }
    },
    async clearStrip() {
      try {
        await this.fetchJson('/api/led/clear', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: '{}',
        });
        this.setStatus('LED strip cleared.', 'success');
        await this.refreshRuntimeState();
      } catch (error) {
        this.setStatus(error.message, 'error');
      }
    },
    async runChaseTest() {
      try {
        await this.fetchJson('/api/led/chase', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: '{}',
        });
        this.setStatus('Chase test ran on the strip.', 'success');
        await this.refreshRuntimeState();
      } catch (error) {
        this.setStatus(error.message, 'error');
      }
    },
    get isMidiDirty() {
      return (
        (this.draftMidi.input_port_name || '') !== (this.midiPorts.selected_input_port || '') ||
        (this.draftMidi.output_port_name || '') !== (this.midiPorts.selected_output_port || '')
      );
    },
    get prettyRuntimeState() {
      return JSON.stringify(this.runtimeState || {}, null, 2);
    },
    get prettySettings() {
      return JSON.stringify(this.settings || {}, null, 2);
    },
    get statusToneClass() {
      if (this.statusTone === 'success') {
        return 'status-success';
      }
      if (this.statusTone === 'error') {
        return 'status-error';
      }
      if (this.statusTone === 'info') {
        return 'status-info';
      }
      return 'status-idle';
    },
  };
};
