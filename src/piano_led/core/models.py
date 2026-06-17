"""Small shared dataclasses used across runtime, playback, and MIDI services."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class NoteEvent:
    """Normalized note event independent of any specific MIDI library."""

    event_type: str
    note: int
    velocity: int
    source: str

    @classmethod
    def note_on(cls, note: int, velocity: int, source: str) -> "NoteEvent":
        return cls(event_type="note_on", note=note, velocity=velocity, source=source)

    @classmethod
    def note_off(cls, note: int, source: str) -> "NoteEvent":
        return cls(event_type="note_off", note=note, velocity=0, source=source)


@dataclass(frozen=True)
class TimedMidiEvent:
    """One note event scheduled at an absolute playback time in seconds."""

    time_seconds: float
    event: NoteEvent
    track_index: int | None = None
    channel: int | None = None
    hand: str = "unassigned"


@dataclass(frozen=True)
class LoadedMidiSong:
    """Parsed MIDI song data ready for playback scheduling."""

    relative_path: str
    display_title: str
    duration_seconds: float
    events: list[TimedMidiEvent]


@dataclass
class PlaybackState:
    """Serializable runtime state for the first playback slice."""

    status: str = "stopped"
    selected_song_path: str | None = None
    song_title: str | None = None
    duration_seconds: float = 0.0
    elapsed_seconds: float = 0.0
    active_notes: list[int] = field(default_factory=list)
    midi_output_enabled: bool = False
    hand_mode: str = "both"
    error: str | None = None

    def to_dict(self) -> dict:
        """Return a plain dictionary for the state store and JSON responses."""

        return asdict(self)
