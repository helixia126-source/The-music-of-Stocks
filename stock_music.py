"""Stock-market music generator with a Tkinter interface.

First screen: enter a ticker and choose a genre or Custom.
Custom screen: choose instruments, scale, chord progression, tempo,
and which musical layers to include.

Requirements (install in the VS Code terminal):
    py -m pip install numpy yfinance matplotlib mido

Also requires FluidSynth and GeneralUser-GS.sf2 in the project folder
(or in a subfolder of the project folder).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.animation import FuncAnimation
from mido import MidiFile, MidiTrack, Message, MetaMessage
from pathlib import Path
import subprocess
import shutil
import time
import wave
import winsound
import re


# ============================================================
# 1. GENERAL SETTINGS AND GENERAL MIDI INSTRUMENTS
# ============================================================

DEFAULT_PERIOD = "6mo"
SAMPLE_RATE = 44100
TICKS_PER_BEAT = 480

# Durations are expressed in beats, so the tempo selector genuinely
# changes the speed of the generated music.
NOTE_DURATION_BEATS = 0.70
GAP_DURATION_BEATS = 0.12

TREND_WINDOW = 20
BASSLINE_EVERY = 8
VOLATILITY_WINDOW = 10

FLUIDSYNTH_GAIN = 1.0
BASS_CHANNEL_VOLUME = 115
PERCUSSION_CHANNEL_VOLUME = 105

INSTRUMENTS = {
    "piano": 0,
    "bright_piano": 1,
    "electric_piano": 4,
    "music_box": 10,
    "tubular_bells": 14,
    "church_organ": 19,
    "harmonica": 22,  # General MIDI: Harmonica
    "nylon_guitar": 24,  # General MIDI: Acoustic Guitar (nylon)
    "acoustic_guitar": 25,  # General MIDI: Acoustic Guitar (steel-string)
    "electric_guitar": 27,  # General MIDI: Electric Guitar (clean)
    "overdriven_guitar": 29,  # General MIDI: Overdriven Guitar
    "distortion_guitar": 30,  # General MIDI: Distortion Guitar
    "acoustic_bass": 32,
    "violin": 40,
    "cello": 42,
    "double_bass": 43,  # General MIDI: Contrabass (double bass)
    "pizzicato_strings": 45,  # General MIDI: Pizzicato Strings
    "pizzicato_double_bass": 45,  # Pizzicato Strings preset used in the low bass register
    "string_ensemble": 48,
    "choir": 52,
    "trumpet": 56,
    "saxophone": 66,  # General MIDI: Tenor Saxophone
    "baritone_saxophone": 67,  # General MIDI: Baritone Saxophone
    "flute": 73,
    "pan_flute": 75,
    "warm_pad": 89,
}

# Human-readable instrument names shown in the interface.
INSTRUMENT_LABELS = {
    key: key.replace("_", " ").title()
    for key in INSTRUMENTS
}
LABEL_TO_INSTRUMENT = {
    label: key for key, label in INSTRUMENT_LABELS.items()
}


# ============================================================
# 2. GENRE PRESETS: SCALES AND CHORD PROGRESSIONS
# ============================================================

GENRES = {
    "rock": {
        "scale_name": "C minor pentatonic",
        "pitch_classes": [0, 3, 5, 7, 10],
        "progression_name": "i - bVII - IV - i (power chords)",
        "chords": [
            {
                "name": "C5",
                "notes": [60, 67],
                "bass_tones": [36, 43, 48, 55, 60],
            },
            {
                "name": "Bb5",
                "notes": [58, 65],
                "bass_tones": [46, 53, 58],
            },
            {
                "name": "F5",
                "notes": [53, 60],
                "bass_tones": [41, 48, 53, 60],
            },
            {
                "name": "C5",
                "notes": [60, 67],
                "bass_tones": [36, 43, 48, 55, 60],
            },
        ],
    },

    "pop": {
        "scale_name": "C major",
        "pitch_classes": [0, 2, 4, 5, 7, 9, 11],
        "progression_name": "I - V - vi - IV",
        "chords": [
            {
                "name": "C major",
                "notes": [60, 64, 67],
                "bass_tones": [36, 40, 43, 48, 52, 55, 60],
            },
            {
                "name": "G major",
                "notes": [55, 59, 62],
                "bass_tones": [43, 47, 50, 55, 59],
            },
            {
                "name": "A minor",
                "notes": [57, 60, 64],
                "bass_tones": [45, 48, 52, 57, 60],
            },
            {
                "name": "F major",
                "notes": [53, 57, 60],
                "bass_tones": [41, 45, 48, 53, 57, 60],
            },
        ],
    },

    "blues": {
        "scale_name": "C blues scale",
        "pitch_classes": [0, 3, 5, 6, 7, 10],
        "progression_name": "12-bar blues (I7 - IV7 - V7)",
        # A standard 12-bar blues form in C: four bars on I7,
        # two on IV7, two on I7, then V7, IV7, I7, V7.
        "chords": [
            {"name": "C7", "notes": [60, 64, 67, 70],
             "bass_tones": [36, 43, 46, 48, 55, 58, 60]},
            {"name": "C7", "notes": [60, 64, 67, 70],
             "bass_tones": [36, 43, 46, 48, 55, 58, 60]},
            {"name": "C7", "notes": [60, 64, 67, 70],
             "bass_tones": [36, 43, 46, 48, 55, 58, 60]},
            {"name": "C7", "notes": [60, 64, 67, 70],
             "bass_tones": [36, 43, 46, 48, 55, 58, 60]},
            {"name": "F7", "notes": [53, 57, 60, 63],
             "bass_tones": [39, 41, 48, 51, 53, 60]},
            {"name": "F7", "notes": [53, 57, 60, 63],
             "bass_tones": [39, 41, 48, 51, 53, 60]},
            {"name": "C7", "notes": [60, 64, 67, 70],
             "bass_tones": [36, 43, 46, 48, 55, 58, 60]},
            {"name": "C7", "notes": [60, 64, 67, 70],
             "bass_tones": [36, 43, 46, 48, 55, 58, 60]},
            {"name": "G7", "notes": [55, 59, 62, 65],
             "bass_tones": [43, 47, 50, 53, 55, 59]},
            {"name": "F7", "notes": [53, 57, 60, 63],
             "bass_tones": [39, 41, 48, 51, 53, 60]},
            {"name": "C7", "notes": [60, 64, 67, 70],
             "bass_tones": [36, 43, 46, 48, 55, 58, 60]},
            {"name": "G7", "notes": [55, 59, 62, 65],
             "bass_tones": [43, 47, 50, 53, 55, 59]},
        ],
    },

    "soul": {
        "scale_name": "C mixolydian",
        "pitch_classes": [0, 2, 4, 5, 7, 9, 10],
        "progression_name": "I7 - IV7 - ii7 - V7",
        "chords": [
            {
                "name": "C7",
                "notes": [60, 64, 67, 70],
                "bass_tones": [36, 40, 43, 46, 48, 52, 55, 58, 60],
            },
            {
                "name": "F7",
                "notes": [53, 57, 60, 63],
                "bass_tones": [39, 41, 48, 51, 53, 60],
            },
            {
                "name": "D minor 7",
                "notes": [62, 65, 69, 72],
                "bass_tones": [38, 41, 45, 48, 50, 53, 57, 60],
            },
            {
                "name": "G7",
                "notes": [55, 59, 62, 65],
                "bass_tones": [43, 47, 50, 53, 55, 59],
            },
        ],
    },

    "jazz": {
        "scale_name": "C major bebop (with Ab passing tone)",
        "pitch_classes": [0, 2, 4, 5, 7, 8, 9, 11],
        "progression_name": "ii7 - V7 - Imaj7 - vi7",
        "chords": [
            {
                "name": "D minor 7",
                "notes": [62, 65, 69, 72],
                "bass_tones": [38, 41, 45, 48, 50, 53, 57, 60],
            },
            {
                "name": "G7",
                "notes": [55, 59, 62, 65],
                "bass_tones": [43, 47, 50, 53, 55, 59],
            },
            {
                "name": "C major 7",
                "notes": [60, 64, 67, 71],
                "bass_tones": [36, 40, 43, 47, 48, 52, 55, 59, 60],
            },
            {
                "name": "A minor 7",
                "notes": [57, 60, 64, 67],
                "bass_tones": [45, 48, 52, 55, 57, 60],
            },
        ],
    },

    "classical": {
        "scale_name": "C major",
        "pitch_classes": [0, 2, 4, 5, 7, 9, 11],
        "progression_name": "I - IV - V - I",
        "chords": [
            {
                "name": "C major",
                "notes": [60, 64, 67],
                "bass_tones": [36, 40, 43, 48, 52, 55, 60],
            },
            {
                "name": "F major",
                "notes": [60, 65, 69],
                "bass_tones": [41, 45, 48, 53, 57, 60],
            },
            {
                "name": "G major",
                "notes": [59, 62, 67],
                "bass_tones": [43, 47, 50, 55, 59],
            },
            {
                "name": "C major",
                "notes": [60, 64, 67],
                "bass_tones": [36, 40, 43, 48, 52, 55, 60],
            },
        ],
    },
}

GENRE_NAMES = list(GENRES.keys())

# Human-readable names shown in the interface and output.
# Keep the internal key "classical" unchanged so existing preset
# configuration and generation logic continue to work.
GENRE_DISPLAY_NAMES = {
    "classical": "Dramatic Classical",
}
GENRE_LABEL_TO_KEY = {
    GENRE_DISPLAY_NAMES.get(name, name.title()).casefold(): name
    for name in GENRE_NAMES
}

def genre_display_name(genre):
    """Return the user-facing name for an internal genre key."""
    return GENRE_DISPLAY_NAMES.get(genre, genre.replace("_", " ").title())

# Extract unique scales from the six genre presets. This means the
# Custom screen offers exactly the scales already defined above.
SCALE_PRESETS = {}
for _genre_name, _settings in GENRES.items():
    SCALE_PRESETS.setdefault(
        _settings["scale_name"],
        list(_settings["pitch_classes"])
    )

# Each progression is labelled by its source genre so that repeated
# progression names, if any, remain distinguishable in the GUI.
PROGRESSION_PRESETS = {}
for _genre_name, _settings in GENRES.items():
    _label = f"{genre_display_name(_genre_name)} — {_settings['progression_name']}"
    PROGRESSION_PRESETS[_label] = {
        "source_genre": _genre_name,
        "chords": _settings["chords"],
    }

# Representative default instruments and tempos for each genre.
# These are defaults for a quick genre selection; Custom can override them.
GENRE_DEFAULTS = {
    "rock":      {"melody": "electric_guitar", "backing": "distortion_guitar", "tempo": 200},
    "pop":       {"melody": "nylon_guitar", "backing": "electric_piano", "tempo": 120},
    "blues":     {"melody": "harmonica", "backing": "nylon_guitar", "tempo": 89},
    "soul":      {"melody": "baritone_saxophone", "backing": "pizzicato_double_bass", "tempo": 90},
    "jazz":      {"melody": "bright_piano", "backing": "acoustic_bass", "tempo": 135},
    "classical": {"melody": "piano", "backing": "cello", "tempo": 100},
}


def make_scale(pitch_classes, first_note, last_note):
    """Return MIDI notes in a register belonging to the selected scale."""
    pitch_class_set = set(pitch_classes)
    return np.array(
        [note for note in range(first_note, last_note + 1)
         if note % 12 in pitch_class_set],
        dtype=int
    )


def add_timed_events(track, events):
    """Append (absolute_tick, priority, message) events as MIDI delta times."""
    events.sort(key=lambda event: (event[0], event[1]))
    previous_tick = 0
    for tick, _priority, message in events:
        delta_time = tick - previous_tick
        track.append(message.copy(time=delta_time))
        previous_tick = tick


def find_project_files(script_path):
    """Locate project folder, the actual SoundFont file and FluidSynth."""
    script_folder = script_path.resolve().parent
    if script_folder.name.lower() == "stock_music.py":
        project_folder = script_folder.parent
    else:
        project_folder = script_folder

    soundfont_candidates = sorted(
        path for path in project_folder.rglob("*")
        if path.is_file() and path.name.lower() == "generaluser-gs.sf2"
    )
    if not soundfont_candidates:
        raise FileNotFoundError(
            "Cannot find the actual GeneralUser-GS.sf2 file. "
            "Check that it is extracted somewhere inside your Numpytest folder."
        )
    soundfont_path = soundfont_candidates[0].resolve()

    fluidsynth_exe = shutil.which("fluidsynth")
    if fluidsynth_exe is None:
        candidates = sorted(
            path for path in project_folder.rglob("fluidsynth.exe")
            if path.is_file()
        )
        if candidates:
            fluidsynth_exe = str(candidates[0].resolve())
    if fluidsynth_exe is None:
        raise FileNotFoundError(
            "Cannot find fluidsynth.exe. Check that FluidSynth is extracted "
            "inside your Numpytest folder."
        )
    return project_folder, soundfont_path, fluidsynth_exe


def normalise(values, low_percentile=5, high_percentile=95, fallback=0.5):
    """Robustly map a numerical array to [0, 1]."""
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return values.copy()
    low, high = np.percentile(values, [low_percentile, high_percentile])
    if np.isclose(low, high):
        return np.full(len(values), fallback, dtype=float)
    return np.clip((values - low) / (high - low), 0, 1)


def generate_music(settings, script_path):
    """Download data, construct MIDI, render WAV and animate the stock chart."""
    ticker = settings["ticker"].strip().upper()
    genre = settings["genre"]
    scale_name = settings["scale_name"]
    pitch_classes = settings["pitch_classes"]
    progression_name = settings["progression_name"]
    chord_progression = settings["chords"]
    melody_instrument = settings["melody_instrument"]
    backing_instrument = settings["backing_instrument"]
    tempo = int(settings["tempo"])
    include_melody = settings["include_melody"]
    include_bass = settings["include_bass"]
    include_chords = settings["include_chords"]
    include_percussion = settings["include_percussion"]

    if not ticker:
        raise ValueError("Enter a stock ticker symbol.")
    if not 40 <= tempo <= 240:
        raise ValueError("Tempo must be between 40 and 240 BPM.")
    if not any([include_melody, include_bass, include_chords, include_percussion]):
        raise ValueError("Select at least one musical layer to include.")

    melody_program = INSTRUMENTS[melody_instrument]
    backing_program = INSTRUMENTS[backing_instrument]

    project_folder, soundfont_path, fluidsynth_exe = find_project_files(script_path)
    print("Project folder:", project_folder)
    print("SoundFont:", soundfont_path)
    print("FluidSynth:", fluidsynth_exe)

    # --------------------------------------------------------
    # Download stock market data
    # --------------------------------------------------------
    print(f"\nDownloading {ticker} stock data...")
    data = yf.download(
        ticker,
        period=DEFAULT_PERIOD,
        interval="1d",
        auto_adjust=True,
        multi_level_index=False,
        progress=False
    )
    if data.empty:
        raise ValueError(
            f"No stock market data was downloaded for {ticker}. "
            "Check the ticker symbol and your internet connection."
        )

    closing_prices = data["Close"].dropna()
    daily_returns = closing_prices.pct_change().dropna()
    if daily_returns.empty:
        raise ValueError("Not enough stock market data to create music.")

    returns = daily_returns.to_numpy(dtype=float)
    volumes = (
        data.loc[daily_returns.index, "Volume"]
        .fillna(0)
        .to_numpy(dtype=float)
    )
    print("Stock data downloaded. Trading days:", len(returns))

    # --------------------------------------------------------
    # Select melody and bass scales
    # --------------------------------------------------------
    melody_scale = make_scale(pitch_classes, 60, 84)
    bass_scale = make_scale(pitch_classes, 36, 60)
    if len(melody_scale) == 0 or len(bass_scale) == 0:
        raise ValueError("The selected scale contains no usable notes.")

    # Daily returns -> melody pitches.
    normalised_returns = normalise(returns)
    melody_positions = np.rint(
        normalised_returns * (len(melody_scale) - 1)
    ).astype(int)
    melody_notes = melody_scale[melody_positions]
    # Pizzicato Double Bass uses the same General MIDI Pizzicato Strings
    # preset, but is placed one octave lower when selected for the melody.
    # In the backing role, it already uses the low C2-C4 bass register.
    if melody_instrument == "pizzicato_double_bass":
        melody_notes = np.maximum(melody_notes - 12, 24)

    # Trading volume -> melody velocity.
    sqrt_volumes = np.sqrt(np.maximum(volumes, 0))
    normalised_volumes = normalise(sqrt_volumes)
    melody_velocities = (40 + 80 * normalised_volumes).astype(int)

    # --------------------------------------------------------
    # Rolling volatility -> percussion intensity
    # --------------------------------------------------------
    rolling_volatility = daily_returns.rolling(
        window=VOLATILITY_WINDOW,
        min_periods=2
    ).std(ddof=0).fillna(0)
    volatility_values = rolling_volatility.to_numpy(dtype=float)
    normalised_volatility = normalise(
        volatility_values,
        fallback=0.0
    )

    # --------------------------------------------------------
    # Long-term trend -> bass notes
    # --------------------------------------------------------
    trend_average = closing_prices.rolling(
        window=TREND_WINDOW,
        min_periods=TREND_WINDOW
    ).mean()
    long_term_trend = trend_average.pct_change(
        periods=BASSLINE_EVERY,
        fill_method=None
    )
    long_term_trend = (
        long_term_trend.reindex(daily_returns.index)
        .fillna(0)
        .to_numpy(dtype=float)
    )

    bass_sample_indices = np.arange(
        0, len(long_term_trend), BASSLINE_EVERY
    )
    bass_trend_values = np.array([
        np.mean(long_term_trend[i:min(i + BASSLINE_EVERY, len(long_term_trend))])
        for i in bass_sample_indices
    ])
    max_trend = np.percentile(np.abs(bass_trend_values), 95)
    if np.isclose(max_trend, 0):
        normalised_bass = np.full(len(bass_trend_values), 0.5)
    else:
        normalised_bass = np.clip(
            0.5 + 0.5 * bass_trend_values / max_trend,
            0,
            1
        )
    bass_positions = np.rint(
        normalised_bass * (len(bass_scale) - 1)
    ).astype(int)
    bass_notes = bass_scale[bass_positions]

    # --------------------------------------------------------
    # Chord progression and bass harmonisation
    # --------------------------------------------------------
    chords = [
        chord_progression[i % len(chord_progression)]["notes"]
        for i in range(len(bass_notes))
    ]
    if include_chords:
        bass_notes = np.array([
            min(
                chord_progression[i % len(chord_progression)]["bass_tones"],
                key=lambda tone: abs(tone - int(note))
            )
            for i, note in enumerate(bass_notes)
        ], dtype=int)

    # Trend strength drives bass and chord velocity.
    trend_strength = np.abs(bass_trend_values)
    strength_limit = np.percentile(trend_strength, 95) if len(trend_strength) else 0
    if np.isclose(strength_limit, 0):
        normalised_strength = np.zeros(len(trend_strength))
    else:
        normalised_strength = np.clip(
            trend_strength / strength_limit,
            0,
            1
        )
    bass_velocities = (75 + 45 * normalised_strength).astype(int)
    chord_velocities = (55 + 20 * normalised_strength).astype(int)

    print("Musical scale:", scale_name)
    print("Chord progression:", progression_name)

    # --------------------------------------------------------
    # MIDI timing: tempo now directly changes playback speed.
    # --------------------------------------------------------
    ticks_per_beat = TICKS_PER_BEAT
    tempo_microseconds = int(60_000_000 / tempo)
    ticks_per_second = ticks_per_beat * 1_000_000 / tempo_microseconds
    note_ticks = max(1, round(NOTE_DURATION_BEATS * ticks_per_beat))
    gap_ticks = max(0, round(GAP_DURATION_BEATS * ticks_per_beat))
    step_ticks = note_ticks + gap_ticks
    seconds_per_step = (NOTE_DURATION_BEATS + GAP_DURATION_BEATS) * 60.0 / tempo
    song_end_tick = (len(returns) - 1) * step_ticks + note_ticks

    # --------------------------------------------------------
    # Create MIDI file and tracks
    # --------------------------------------------------------
    midi = MidiFile(type=1, ticks_per_beat=ticks_per_beat)
    conductor_track = MidiTrack()
    midi.tracks.append(conductor_track)
    conductor_track.append(MetaMessage(
        "set_tempo", tempo=tempo_microseconds, time=0
    ))

    melody_track = None
    bass_track = None
    chord_track = None
    percussion_track = None

    if include_melody:
        melody_track = MidiTrack()
        midi.tracks.append(melody_track)
        melody_track.append(Message(
            "program_change", channel=0, program=melody_program, time=0
        ))
        melody_events = []
        for i, (note, velocity) in enumerate(zip(melody_notes, melody_velocities)):
            start_tick = i * step_ticks
            end_tick = start_tick + note_ticks
            melody_events.append((
                start_tick, 1,
                Message("note_on", channel=0, note=int(note),
                        velocity=int(velocity), time=0)
            ))
            melody_events.append((
                end_tick, 0,
                Message("note_off", channel=0, note=int(note),
                        velocity=0, time=0)
            ))
        add_timed_events(melody_track, melody_events)
        print("Melody track created.")

    if include_bass:
        bass_track = MidiTrack()
        midi.tracks.append(bass_track)
        bass_track.append(Message(
            "program_change", channel=1, program=backing_program, time=0
        ))
        bass_track.append(Message(
            "control_change", channel=1, control=7,
            value=int(np.clip(BASS_CHANNEL_VOLUME, 0, 127)), time=0
        ))
        bass_events = []
        for i, (note, velocity) in enumerate(zip(bass_notes, bass_velocities)):
            start_tick = int(bass_sample_indices[i] * step_ticks)
            if i < len(bass_notes) - 1:
                end_tick = int(bass_sample_indices[i + 1] * step_ticks)
            else:
                end_tick = song_end_tick
            end_tick = max(end_tick, start_tick + 1)
            bass_events.append((
                start_tick, 1,
                Message("note_on", channel=1, note=int(note),
                        velocity=int(velocity), time=0)
            ))
            bass_events.append((
                end_tick, 0,
                Message("note_off", channel=1, note=int(note),
                        velocity=0, time=0)
            ))
        add_timed_events(bass_track, bass_events)
        print("Bassline track created.")

    if include_chords:
        chord_track = MidiTrack()
        midi.tracks.append(chord_track)
        chord_track.append(Message(
            "program_change", channel=2, program=melody_program, time=0
        ))
        chord_events = []
        for i, (chord, velocity) in enumerate(zip(chords, chord_velocities)):
            start_tick = int(bass_sample_indices[i] * step_ticks)
            if i < len(chords) - 1:
                end_tick = int(bass_sample_indices[i + 1] * step_ticks)
            else:
                end_tick = song_end_tick
            end_tick = max(end_tick, start_tick + 1)
            for chord_note in chord:
                chord_events.append((
                    start_tick, 1,
                    Message("note_on", channel=2, note=int(chord_note),
                            velocity=int(velocity), time=0)
                ))
                chord_events.append((
                    end_tick, 0,
                    Message("note_off", channel=2, note=int(chord_note),
                            velocity=0, time=0)
                ))
        add_timed_events(chord_track, chord_events)
        print("Chord track created.")

    if include_percussion:
        percussion_track = MidiTrack()
        midi.tracks.append(percussion_track)
        # MIDI channel 9 is the standard percussion channel.
        percussion_track.append(Message(
            "control_change", channel=9, control=7,
            value=int(np.clip(PERCUSSION_CHANNEL_VOLUME, 0, 127)), time=0
        ))
        percussion_events = []
        percussion_hit_count = 0
        drum_note_ticks = max(1, round(0.10 * ticks_per_second))

        # General MIDI percussion note numbers.
        DRUM_BASS_DRUM = 36
        DRUM_SNARE = 38
        DRUM_CLOSED_HIHAT = 42
        DRUM_OPEN_HIHAT = 46
        DRUM_CRASH = 49
        DRUM_RIDE = 51
        regular_cymbal = DRUM_RIDE if genre == "jazz" else DRUM_CLOSED_HIHAT

        def add_percussion_hit(absolute_tick, drum_note, velocity):
            nonlocal_placeholder = None  # Keeps the nested function side-effect-free except for its list.
            percussion_events.append((
                int(absolute_tick), 1,
                Message("note_on", channel=9, note=int(drum_note),
                        velocity=int(np.clip(round(velocity), 1, 127)), time=0)
            ))
            percussion_events.append((
                int(absolute_tick + drum_note_ticks), 0,
                Message("note_off", channel=9, note=int(drum_note),
                        velocity=0, time=0)
            ))

        for i, volatility_level in enumerate(normalised_volatility):
            step_start = int(i * step_ticks)
            add_percussion_hit(
                step_start, regular_cymbal,
                25 + 65 * volatility_level
            )
            if i % 4 == 0:
                add_percussion_hit(
                    step_start, DRUM_BASS_DRUM,
                    45 + 65 * volatility_level
                )
            if i % 4 == 2:
                add_percussion_hit(
                    step_start, DRUM_SNARE,
                    40 + 70 * volatility_level
                )
            if volatility_level >= 0.40:
                add_percussion_hit(
                    step_start + step_ticks // 2,
                    regular_cymbal,
                    32 + 60 * volatility_level
                )
            if volatility_level >= 0.70:
                add_percussion_hit(
                    step_start + (3 * step_ticks) // 4,
                    DRUM_OPEN_HIHAT,
                    42 + 65 * volatility_level
                )
            previous_volatility = normalised_volatility[i - 1] if i > 0 else 0
            if volatility_level >= 0.90 and previous_volatility < 0.90:
                add_percussion_hit(
                    step_start, DRUM_CRASH,
                    75 + 45 * volatility_level
                )

        add_timed_events(percussion_track, percussion_events)
        percussion_hit_count = len(percussion_events) // 2
        print("Percussion track created. Drum hits:", percussion_hit_count)
    else:
        percussion_hit_count = 0

    # End all tracks after the notes and a short soundfont release tail.
    tail_ticks = round(1.5 * ticks_per_second)
    for track in midi.tracks:
        track.append(MetaMessage("end_of_track", time=tail_ticks))

    safe_ticker = re.sub(r"[^A-Za-z0-9._-]+", "_", ticker).lower()
    safe_genre = re.sub(r"[^A-Za-z0-9._-]+", "_", genre).lower()
    safe_scale = re.sub(r"[^A-Za-z0-9._-]+", "_", scale_name).lower()
    midi_filename = f"{safe_ticker}_{safe_genre}_{safe_scale}_stock_music.mid"
    midi_path = project_folder / midi_filename
    midi.save(str(midi_path))
    print("MIDI file saved:", midi_path)

    # --------------------------------------------------------
    # Render using FluidSynth
    # --------------------------------------------------------
    wav_filename = f"{safe_ticker}_{safe_genre}_{safe_scale}_stock_music.wav"
    wav_path = project_folder / wav_filename
    command = [
        str(fluidsynth_exe),
        "-ni", "-q",
        "-r", str(SAMPLE_RATE),
        "-g", str(FLUIDSYNTH_GAIN),
        "-F", str(wav_path),
        "-T", "wav",
        str(soundfont_path),
        str(midi_path),
    ]
    print("Rendering music using FluidSynth...")
    try:
        subprocess.run(
            command, check=True, capture_output=True,
            text=True, errors="replace"
        )
    except subprocess.CalledProcessError as error:
        print("FluidSynth rendering failed:")
        print(error.stderr or error.stdout)
        raise RuntimeError("FluidSynth could not render the WAV file.") from error
    if not wav_path.is_file():
        raise RuntimeError("FluidSynth finished but did not create the WAV file.")

    with wave.open(str(wav_path), "rb") as audio_file:
        audio_duration = audio_file.getnframes() / audio_file.getframerate()
    if audio_duration <= 0:
        raise ValueError("The generated WAV file contains no audio.")

    print("\n================================")
    print("MUSIC SUCCESSFULLY GENERATED")
    print("================================")
    print("Ticker:", ticker)
    print("Genre:", genre_display_name(genre))
    print("Scale:", scale_name)
    print("Chord progression:", progression_name)
    print("Melody instrument:", INSTRUMENT_LABELS[melody_instrument])
    print("Backing instrument:", INSTRUMENT_LABELS[backing_instrument])
    print("Tempo:", tempo, "BPM")
    print("MIDI:", midi_filename)
    print("WAV:", wav_filename)
    print("================================")

    # --------------------------------------------------------
    # Animated chart, synchronised to the generated audio
    # --------------------------------------------------------
    plot_dates = daily_returns.index
    plot_prices = closing_prices.reindex(plot_dates).to_numpy(dtype=float)
    date_numbers = mdates.date2num(plot_dates.to_pydatetime())
    if len(plot_prices) < 2:
        raise ValueError("At least two trading days are needed for the graph animation.")

    fig, ax = plt.subplots(figsize=(13, 7))
    ax.plot(
        plot_dates, plot_prices,
        color="royalblue", linewidth=1.8,
        label="Closing share price"
    )
    ax.set_title(
        f"{ticker} Stock Market and Music Visualisation "
        f"({genre_display_name(genre)} – {scale_name})",
        fontsize=15
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Share Price (USD)")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.margins(y=0.12)

    cursor = ax.axvline(
        x=date_numbers[0], color="red", linestyle="--",
        linewidth=2, label="Current playback position"
    )
    marker, = ax.plot(
        [date_numbers[0]], [plot_prices[0]],
        marker="o", markersize=8, color="red", zorder=5
    )
    status_text = ax.text(
        0.02, 0.95, "Preparing playback...",
        transform=ax.transAxes, fontsize=10,
        verticalalignment="top",
        bbox={"facecolor": "white", "alpha": 0.88, "edgecolor": "grey"}
    )
    ax.legend(loc="lower right")
    fig.autofmt_xdate()

    playback_state = {"start_time": None, "finished": False}

    def initialise_animation():
        cursor.set_xdata([date_numbers[0], date_numbers[0]])
        marker.set_data([date_numbers[0]], [plot_prices[0]])
        status_text.set_text("Starting music...")
        return cursor, marker, status_text

    def update_animation(_frame):
        if playback_state["start_time"] is None:
            winsound.PlaySound(
                str(wav_path),
                winsound.SND_FILENAME | winsound.SND_ASYNC
            )
            playback_state["start_time"] = time.perf_counter()
            print("Music playback started!")

        elapsed = time.perf_counter() - playback_state["start_time"]
        data_position = min(
            max(elapsed / seconds_per_step, 0),
            len(plot_prices) - 1
        )
        left_index = int(data_position)
        right_index = min(left_index + 1, len(plot_prices) - 1)
        fraction = data_position - left_index

        current_date = (
            date_numbers[left_index]
            + fraction * (date_numbers[right_index] - date_numbers[left_index])
        )
        current_price = (
            plot_prices[left_index]
            + fraction * (plot_prices[right_index] - plot_prices[left_index])
        )
        current_volatility = (
            volatility_values[left_index]
            + fraction * (volatility_values[right_index] - volatility_values[left_index])
        )

        cursor.set_xdata([current_date, current_date])
        marker.set_data([current_date], [current_price])
        display_index = min(round(data_position), len(plot_prices) - 1)
        display_date = plot_dates[display_index].strftime("%d %B %Y")
        status_text.set_text(
            f"Date: {display_date}\n"
            f"Share price: {current_price:.2f} USD\n"
            f"{VOLATILITY_WINDOW}-day volatility: {current_volatility * 100:.2f}%\n"
            f"Genre: {genre_display_name(genre)}\n"
            f"Tempo: {tempo} BPM\n"
            f"Playback: {elapsed:.1f} / {audio_duration:.1f} seconds"
        )

        if elapsed >= audio_duration and not playback_state["finished"]:
            cursor.set_xdata([date_numbers[-1], date_numbers[-1]])
            marker.set_data([date_numbers[-1]], [plot_prices[-1]])
            status_text.set_text(
                "Music finished!\n"
                f"Final share price: {plot_prices[-1]:.2f} USD"
            )
            winsound.PlaySound(None, 0)
            playback_state["finished"] = True
            animation.event_source.stop()
            print("Music playback finished!")
        return cursor, marker, status_text

    def stop_audio(_event):
        winsound.PlaySound(None, 0)

    fig.canvas.mpl_connect("close_event", stop_audio)
    animation = FuncAnimation(
        fig, update_animation,
        init_func=initialise_animation,
        interval=30, blit=False,
        repeat=False, cache_frame_data=False
    )
    plt.tight_layout()
    plt.show()


# ============================================================
# 3. TKINTER INTERFACE: FIRST SCREEN
# ============================================================

class StockMusicApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Market Music Generator")
        self.root.geometry("680x520")
        self.root.minsize(600, 460)
        self.root.configure(bg="#f3f5f8")

        self.style = ttk.Style()
        try:
            self.style.theme_use("clam")
        except tk.TclError:
            pass
        self.style.configure("TFrame", background="#f3f5f8")
        self.style.configure("Card.TFrame", background="white")
        self.style.configure("Title.TLabel", background="#f3f5f8",
                             foreground="#172033", font=("Segoe UI", 19, "bold"))
        self.style.configure("Subtitle.TLabel", background="#f3f5f8",
                             foreground="#596579", font=("Segoe UI", 10))
        self.style.configure("Field.TLabel", background="white",
                             foreground="#263247", font=("Segoe UI", 10, "bold"))
        self.style.configure("TButton", font=("Segoe UI", 10), padding=(12, 8))
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"),
                             padding=(14, 9))
        self.style.configure("TCheckbutton", background="white",
                             font=("Segoe UI", 10))
        self.style.configure("TRadiobutton", background="white",
                             font=("Segoe UI", 10))

        self.ticker_var = tk.StringVar(value="AAPL")
        self.genre_var = tk.StringVar(value="Pop")
        self.status_var = tk.StringVar(value="Choose a genre or customise your composition.")
        self.custom_vars = {}

        self.show_start_screen()

    def clear_window(self):
        # The Return shortcut belongs only to the first screen. Clear it
        # before rebuilding a screen so Enter in a custom field does not
        # unexpectedly recreate the custom form.
        self.root.unbind("<Return>")
        for widget in self.root.winfo_children():
            widget.destroy()

    def page_header(self, title, subtitle):
        ttk.Label(self.root, text=title, style="Title.TLabel").pack(
            anchor="w", padx=30, pady=(24, 4)
        )
        ttk.Label(self.root, text=subtitle, style="Subtitle.TLabel",
                  wraplength=550).pack(anchor="w", padx=30, pady=(0, 18))

    def make_card(self):
        card = ttk.Frame(self.root, style="Card.TFrame", padding=22)
        card.pack(fill="both", expand=True, padx=30, pady=(0, 18))
        return card

    def show_start_screen(self):
        self.clear_window()
        self.root.geometry("680x520")
        self.root.minsize(600, 460)
        self.page_header(
            "Stock Market Music Generator",
            "Turn historical share-price movements into a multi-instrument composition."
        )
        card = self.make_card()

        ttk.Label(card, text="Stock ticker", style="Field.TLabel").pack(anchor="w")
        ticker_entry = ttk.Entry(card, textvariable=self.ticker_var,
                                 font=("Segoe UI", 12), width=30)
        ticker_entry.pack(fill="x", pady=(6, 18), ipady=5)
        ticker_entry.focus_set()

        ttk.Label(card, text="Choose a musical genre", style="Field.TLabel").pack(anchor="w")
        genre_combo = ttk.Combobox(
            card,
            textvariable=self.genre_var,
            values=[genre_display_name(name) for name in GENRE_NAMES] + ["Custom"],
            state="readonly",
            font=("Segoe UI", 11)
        )
        genre_combo.pack(fill="x", pady=(6, 12), ipady=4)

        genre_descriptions = (
            "Rock · Pop · Blues · Soul · Jazz · Dramatic Classical\n"
            "Choose Custom to select instruments, scale, progression, tempo and layers."
        )
        ttk.Label(card, text=genre_descriptions, background="white",
                  foreground="#596579", justify="left",
                  font=("Segoe UI", 9), wraplength=510).pack(anchor="w", pady=(0, 18))

        ttk.Button(
            card,
            text="Continue",
            style="Accent.TButton",
            command=self.continue_from_start
        ).pack(anchor="e")

        ttk.Label(self.root, textvariable=self.status_var,
                  background="#f3f5f8", foreground="#596579",
                  wraplength=550).pack(anchor="w", padx=30, pady=(0, 16))

        self.root.bind("<Return>", lambda _event: self.continue_from_start())

    def continue_from_start(self):
        ticker = self.ticker_var.get().strip().upper()
        selected_label = self.genre_var.get().strip()
        selected = GENRE_LABEL_TO_KEY.get(
            selected_label.casefold(), selected_label.lower()
        )
        if not ticker:
            messagebox.showerror("Ticker required", "Enter a stock ticker symbol, for example AAPL.")
            return

        if selected == "custom":
            self.show_custom_screen()
            return

        if selected not in GENRES:
            messagebox.showerror("Choose a genre", "Select one of the six genres or Custom.")
            return

        defaults = GENRE_DEFAULTS[selected]
        genre_settings = GENRES[selected]
        settings = {
            "ticker": ticker,
            "genre": selected,
            "scale_name": genre_settings["scale_name"],
            "pitch_classes": list(genre_settings["pitch_classes"]),
            "progression_name": genre_settings["progression_name"],
            "chords": genre_settings["chords"],
            "melody_instrument": defaults["melody"],
            "backing_instrument": defaults["backing"],
            "tempo": defaults["tempo"],
            "include_melody": True,
            "include_bass": True,
            "include_chords": True,
            "include_percussion": True,
        }
        self.launch_generation(settings)

    # ========================================================
    # 4. TKINTER INTERFACE: CUSTOM SETTINGS SCREEN
    # ========================================================

    def show_custom_screen(self):
        self.clear_window()
        self.root.geometry("850x720")
        self.root.minsize(760, 650)
        self.page_header(
            "Custom composition",
            f"Ticker: {self.ticker_var.get().strip().upper()}  ·  Choose each musical element."
        )
        card = self.make_card()

        self.custom_vars = {
            "melody": tk.StringVar(value=INSTRUMENT_LABELS["piano"]),
            "backing": tk.StringVar(value=INSTRUMENT_LABELS["acoustic_bass"]),
            "scale": tk.StringVar(value="C major"),
            "progression": tk.StringVar(value=next(iter(PROGRESSION_PRESETS))),
            "tempo": tk.StringVar(value="120"),
            "include_melody": tk.BooleanVar(value=True),
            "include_bass": tk.BooleanVar(value=True),
            "include_chords": tk.BooleanVar(value=True),
            "include_percussion": tk.BooleanVar(value=True),
        }

        def add_field(label, variable, values, row):
            ttk.Label(card, text=label, style="Field.TLabel").grid(
                row=row, column=0, sticky="w", padx=(0, 18), pady=7
            )
            combo = ttk.Combobox(
                card, textvariable=variable, values=values,
                state="readonly", font=("Segoe UI", 9), width=38
            )
            combo.grid(row=row, column=1, sticky="ew", pady=7)
            return combo

        card.columnconfigure(1, weight=1)
        instrument_values = list(INSTRUMENT_LABELS.values())
        scale_values = list(SCALE_PRESETS.keys())
        progression_values = list(PROGRESSION_PRESETS.keys())

        add_field("Melody instrument", self.custom_vars["melody"], instrument_values, 0)
        add_field("Backing instrument", self.custom_vars["backing"], instrument_values, 1)
        add_field("Musical scale", self.custom_vars["scale"], scale_values, 2)
        add_field("Chord progression", self.custom_vars["progression"], progression_values, 3)

        ttk.Label(card, text="Tempo (BPM)", style="Field.TLabel").grid(
            row=4, column=0, sticky="w", padx=(0, 18), pady=7
        )
        tempo_spin = ttk.Spinbox(
            card, from_=40, to=240, increment=1,
            textvariable=self.custom_vars["tempo"], width=10,
            font=("Segoe UI", 10)
        )
        tempo_spin.grid(row=4, column=1, sticky="w", pady=7)

        ttk.Separator(card).grid(row=5, column=0, columnspan=2,
                                 sticky="ew", pady=(14, 10))
        ttk.Label(card, text="Include musical layers", style="Field.TLabel").grid(
            row=6, column=0, columnspan=2, sticky="w", pady=(0, 5)
        )

        layer_frame = ttk.Frame(card, style="Card.TFrame")
        layer_frame.grid(row=7, column=0, columnspan=2, sticky="ew")
        layer_options = [
            ("include_melody", "Melody"),
            ("include_bass", "Bassline"),
            ("include_chords", "Chord accompaniment"),
            ("include_percussion", "Percussion"),
        ]
        for index, (key, label) in enumerate(layer_options):
            check = ttk.Checkbutton(
                layer_frame, text=label,
                variable=self.custom_vars[key]
            )
            check.grid(row=index // 2, column=index % 2,
                       sticky="w", padx=(0, 22), pady=5)

        ttk.Label(
            card,
            text=(
                "The backing instrument is used for the bassline. "
                "Chords use the selected melody instrument.\n"
                "Scale and progression can be mixed freely, but some combinations "
                "may contain chord notes outside the selected scale."
            ),
            background="white", foreground="#596579",
            wraplength=650, font=("Segoe UI", 8)
        ).grid(row=8, column=0, columnspan=2, sticky="w", pady=(12, 0))

        buttons = ttk.Frame(self.root, style="TFrame")
        buttons.pack(fill="x", padx=30, pady=(0, 8))
        ttk.Button(buttons, text="Back", command=self.show_start_screen).pack(side="left")
        ttk.Button(
            buttons, text="Generate music", style="Accent.TButton",
            command=self.generate_custom
        ).pack(side="right")

        ttk.Label(self.root, textvariable=self.status_var,
                  background="#f3f5f8", foreground="#596579",
                  wraplength=550).pack(anchor="w", padx=30, pady=(0, 14))

    def generate_custom(self):
        ticker = self.ticker_var.get().strip().upper()
        if not ticker:
            messagebox.showerror("Ticker required", "Enter a stock ticker symbol.")
            return

        try:
            tempo = int(self.custom_vars["tempo"].get())
        except ValueError:
            messagebox.showerror("Invalid tempo", "Enter a whole-number tempo between 40 and 240 BPM.")
            return
        if not 40 <= tempo <= 240:
            messagebox.showerror("Invalid tempo", "Tempo must be between 40 and 240 BPM.")
            return

        selected_scale = self.custom_vars["scale"].get()
        selected_progression = self.custom_vars["progression"].get()
        progression_data = PROGRESSION_PRESETS[selected_progression]

        settings = {
            "ticker": ticker,
            "genre": "custom",
            "scale_name": selected_scale,
            "pitch_classes": SCALE_PRESETS[selected_scale],
            "progression_name": selected_progression,
            "chords": progression_data["chords"],
            "melody_instrument": LABEL_TO_INSTRUMENT[self.custom_vars["melody"].get()],
            "backing_instrument": LABEL_TO_INSTRUMENT[self.custom_vars["backing"].get()],
            "tempo": tempo,
            "include_melody": self.custom_vars["include_melody"].get(),
            "include_bass": self.custom_vars["include_bass"].get(),
            "include_chords": self.custom_vars["include_chords"].get(),
            "include_percussion": self.custom_vars["include_percussion"].get(),
        }

        if not any([
            settings["include_melody"],
            settings["include_bass"],
            settings["include_chords"],
            settings["include_percussion"],
        ]):
            messagebox.showerror(
                "No musical layers selected",
                "Select at least one layer: melody, bassline, chords or percussion."
            )
            return

        self.launch_generation(settings)

    def launch_generation(self, settings):
        """Hide the settings window, generate the composition, then restore it."""
        summary = (
            f"Generating {settings['ticker']} ({genre_display_name(settings['genre'])})... "
            "The graph will open when the WAV file is ready."
        )
        self.status_var.set(summary)
        self.root.update_idletasks()
        self.root.withdraw()
        try:
            generate_music(settings, Path(__file__))
        except Exception as error:
            # Stop any previous asynchronous WAV playback before reporting an error.
            try:
                winsound.PlaySound(None, 0)
            except Exception:
                pass
            self.root.deiconify()
            self.status_var.set("Generation failed. See the error message for details.")
            messagebox.showerror(
                "Could not generate the composition",
                f"{error}\n\nMore details may be available in the VS Code terminal."
            )
        else:
            self.root.deiconify()
            self.status_var.set(
                "Composition finished. Change your settings to generate another version."
            )


def main():
    root = tk.Tk()
    StockMusicApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

