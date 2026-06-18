window.songsPage = function songsPage() {
  return {
    songs: [],
    selectionState: null,
    selectedSongPath: '',
    savedSongPath: '',
    currentHandConfigPath: '',
    localConfig: {
      left_hand_tracks: [],
      right_hand_tracks: [],
      left_hand_channels: [],
      right_hand_channels: [],
    },
    savedConfig: {
      left_hand_tracks: [],
      right_hand_tracks: [],
      left_hand_channels: [],
      right_hand_channels: [],
    },
    handSummary: {
      relative_path: '',
      display_title: '',
      track_indices: [],
      channels: [],
    },
    invalidState: {
      left_hand_tracks: [],
      right_hand_tracks: [],
      left_hand_channels: [],
      right_hand_channels: [],
    },
    statusMessage: '',
    statusTone: 'idle',
    isLoading: false,
    pollHandle: null,
    async init() {
      await this.refreshSongs();
      await this.refreshHandSetup();
      this.pollHandle = window.setInterval(async () => {
        await this.refreshSongs();
        await this.refreshHandSetup();
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
    cloneConfig(config) {
      return {
        left_hand_tracks: [...(config.left_hand_tracks || [])],
        right_hand_tracks: [...(config.right_hand_tracks || [])],
        left_hand_channels: [...(config.left_hand_channels || [])],
        right_hand_channels: [...(config.right_hand_channels || [])],
      };
    },
    normalizeConfig(config) {
      return {
        left_hand_tracks: this.sortedNumbers(config.left_hand_tracks || []),
        right_hand_tracks: this.sortedNumbers(config.right_hand_tracks || []),
        left_hand_channels: this.sortedNumbers(config.left_hand_channels || []),
        right_hand_channels: this.sortedNumbers(config.right_hand_channels || []),
      };
    },
    sortedNumbers(values) {
      return [...values].map(Number).sort((left, right) => left - right);
    },
    configsEqual(leftConfig, rightConfig) {
      return JSON.stringify(this.normalizeConfig(leftConfig)) === JSON.stringify(this.normalizeConfig(rightConfig));
    },
    setStatus(message, tone = 'idle') {
      this.statusMessage = message;
      this.statusTone = tone;
    },
    handleSongSelectionChanged() {
      this.setStatus('Song selection changed locally. Save it when you are ready.', 'info');
      this.refreshHandSetup(true);
    },
    markHandConfigDirty() {
      this.localConfig = this.normalizeConfig(this.localConfig);
      this.setStatus('Hand setup changed locally. Save it when you are ready.', 'info');
    },
    async refreshSongs() {
      try {
        const payload = await this.fetchJson('/api/song-selection');
        const pendingSelection = this.selectedSongPath && this.selectedSongPath !== (payload.selected_song_path || '');
        this.songs = payload.songs || [];
        this.selectionState = payload;
        this.savedSongPath = payload.selected_song_path || '';
        if (!pendingSelection) {
          this.selectedSongPath = this.savedSongPath;
        }
        if (this.selectedSongPath && !this.songs.some((song) => song.relative_path === this.selectedSongPath)) {
          this.selectedSongPath = this.savedSongPath;
        }
      } catch (error) {
        this.setStatus(error.message, 'error');
      }
    },
    async refreshHandSetup(forceReload = false) {
      const path = this.activeSongPath;
      if (!path) {
        this.currentHandConfigPath = '';
        this.handSummary = { relative_path: '', display_title: '', track_indices: [], channels: [] };
        this.invalidState = { left_hand_tracks: [], right_hand_tracks: [], left_hand_channels: [], right_hand_channels: [] };
        this.savedConfig = this.cloneConfig(this.localConfig);
        return;
      }
      try {
        const payload = await this.fetchJson('/api/song-hand-config?relative_path=' + encodeURIComponent(path));
        const normalizedSaved = this.normalizeConfig(payload.config || {});
        const samePath = this.currentHandConfigPath === path;
        const preserveLocal = samePath && !forceReload && this.isHandSetupDirty;
        this.handSummary = payload.summary || this.handSummary;
        this.invalidState = payload.invalid || this.invalidState;
        this.savedConfig = normalizedSaved;
        this.currentHandConfigPath = path;
        if (!preserveLocal) {
          this.localConfig = this.cloneConfig(normalizedSaved);
        }
      } catch (error) {
        this.setStatus(error.message, 'error');
      }
    },
    async saveSongSelection() {
      if (!this.selectedSongPath) {
        return;
      }
      this.isLoading = true;
      try {
        const payload = await this.fetchJson('/api/song-selection', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ relative_path: this.selectedSongPath }),
        });
        this.selectionState = payload;
        this.savedSongPath = payload.selected_song_path || this.selectedSongPath;
        this.selectedSongPath = this.savedSongPath;
        this.setStatus('Selected song saved.', 'success');
        await this.refreshHandSetup(true);
      } catch (error) {
        this.setStatus(error.message, 'error');
      } finally {
        this.isLoading = false;
      }
    },
    async saveHandSetup() {
      if (!this.activeSongPath) {
        return;
      }
      this.isLoading = true;
      try {
        const payload = await this.fetchJson('/api/song-hand-config', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            relative_path: this.activeSongPath,
            left_hand_tracks: this.sortedNumbers(this.localConfig.left_hand_tracks),
            right_hand_tracks: this.sortedNumbers(this.localConfig.right_hand_tracks),
            left_hand_channels: this.sortedNumbers(this.localConfig.left_hand_channels),
            right_hand_channels: this.sortedNumbers(this.localConfig.right_hand_channels),
          }),
        });
        this.savedConfig = this.normalizeConfig(payload.config || {});
        this.localConfig = this.cloneConfig(this.savedConfig);
        this.handSummary = payload.summary || this.handSummary;
        this.invalidState = payload.invalid || this.invalidState;
        this.currentHandConfigPath = this.activeSongPath;
        this.setStatus('Hand setup saved.', 'success');
      } catch (error) {
        this.setStatus(error.message, 'error');
      } finally {
        this.isLoading = false;
      }
    },
    get activeSongPath() {
      return this.selectedSongPath || this.savedSongPath || '';
    },
    get isSongDirty() {
      return (this.selectedSongPath || '') !== (this.savedSongPath || '');
    },
    get isHandSetupDirty() {
      if (!this.activeSongPath) {
        return false;
      }
      return !this.configsEqual(this.localConfig, this.savedConfig);
    },
    get prettySelectionState() {
      return JSON.stringify(this.selectionState || { selected_song_path: this.savedSongPath || null, songs: this.songs }, null, 2);
    },
    get prettyHandState() {
      return JSON.stringify(
        {
          path: this.currentHandConfigPath || this.activeSongPath || null,
          summary: this.handSummary,
          saved_config: this.savedConfig,
          local_config: this.normalizeConfig(this.localConfig),
        },
        null,
        2,
      );
    },
    get prettyInvalidState() {
      return JSON.stringify(this.invalidState, null, 2);
    },
    get hasInvalidMappings() {
      return Object.values(this.invalidState).some((values) => values.length > 0);
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
