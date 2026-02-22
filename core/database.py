"""
MashupID - Cross-Platform Song Database & Matching Engine
SQLite backend — works identically on Windows, Linux, macOS, Jetson Nano.
"""

import sqlite3
import os
import threading
import time
import logging
import numpy as np
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple

log = logging.getLogger("MashupID.DB")


# ─── Data Classes ────────────────────────────────────────────────────────────

@dataclass
class SongMetadata:
    song_id:           int
    title:             str
    artist:            str
    album:             str  = ""
    year:              str  = ""
    duration:          float = 0.0
    genre:             str  = ""
    file_path:         str  = ""
    date_added:        str  = ""
    fingerprint_count: int  = 0
    cover_art_path:    str  = ""
    tags:              str  = ""

@dataclass
class MatchResult:
    song_id:              int
    title:                str
    artist:               str
    album:                str
    year:                 str
    genre:                str
    confidence:           float
    match_count:          int
    offset_seconds:       float
    is_mashup_component:  bool
    cover_art_path:       str  = ""
    mashup_segment_start: float = 0.0
    mashup_segment_end:   float = 0.0


# ─── Database ─────────────────────────────────────────────────────────────────

class SongDatabase:
    """
    Thread-safe SQLite fingerprint database.
    db_path uses os.path — works on Windows (C:\\path) and Unix (/path).
    """

    def __init__(self, db_path: str):
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            c = sqlite3.connect(self.db_path, check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.execute("PRAGMA cache_size=10000")
            c.execute("PRAGMA temp_store=MEMORY")
            self._local.conn = c
        return self._local.conn

    def _init_db(self):
        c = self._conn()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS songs (
                song_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                artist      TEXT DEFAULT '',
                album       TEXT DEFAULT '',
                year        TEXT DEFAULT '',
                duration    REAL DEFAULT 0.0,
                genre       TEXT DEFAULT '',
                file_path   TEXT DEFAULT '',
                date_added  TEXT DEFAULT (datetime('now')),
                fp_count    INTEGER DEFAULT 0,
                cover_art   TEXT DEFAULT '',
                tags        TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS fingerprints (
                hash        TEXT NOT NULL,
                time_offset INTEGER NOT NULL,
                song_id     INTEGER NOT NULL,
                FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_fp_hash ON fingerprints(hash);
            CREATE INDEX IF NOT EXISTS idx_fp_song ON fingerprints(song_id);

            CREATE TABLE IF NOT EXISTS history (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp   TEXT DEFAULT (datetime('now')),
                success     INTEGER,
                song_id     INTEGER,
                confidence  REAL,
                mode        TEXT,
                FOREIGN KEY (song_id) REFERENCES songs(song_id) ON DELETE SET NULL
            );
        """)
        c.commit()

    # ── CRUD ─────────────────────────────────────────────────────────────────

    def add_song(
        self,
        title: str,
        artist: str,
        fingerprints: List[Tuple[str, int]],
        album: str = "", year: str = "",
        duration: float = 0.0, genre: str = "",
        file_path: str = "", cover_art: str = "", tags: str = ""
    ) -> int:
        c = self._conn()
        # Upsert
        existing = c.execute(
            "SELECT song_id FROM songs WHERE title=? AND artist=?", (title, artist)
        ).fetchone()

        if existing:
            song_id = existing['song_id']
            c.execute("DELETE FROM fingerprints WHERE song_id=?", (song_id,))
            # Also update metadata so re-indexing refreshes all fields
            c.execute(
                "UPDATE songs SET album=?,year=?,duration=?,genre=?,file_path=?,"
                "cover_art=?,tags=?,fp_count=? WHERE song_id=?",
                (album, year, duration, genre,
                 file_path.replace('\\', '/'), cover_art, tags,
                 len(fingerprints), song_id)
            )
        else:
            cur = c.execute(
                "INSERT INTO songs (title,artist,album,year,duration,genre,file_path,cover_art,tags,fp_count) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (title, artist, album, year, duration, genre,
                 # Normalize path separators for cross-platform storage
                 file_path.replace('\\', '/'), cover_art, tags, len(fingerprints))
            )
            song_id = cur.lastrowid

        c.executemany(
            "INSERT INTO fingerprints (hash, time_offset, song_id) VALUES (?,?,?)",
            [(h, t, song_id) for h, t in fingerprints]
        )
        c.execute("UPDATE songs SET fp_count=? WHERE song_id=?", (len(fingerprints), song_id))
        c.commit()
        return song_id

    def delete_song(self, song_id: int) -> bool:
        c = self._conn()
        c.execute("DELETE FROM fingerprints WHERE song_id=?", (song_id,))
        c.execute("DELETE FROM songs WHERE song_id=?", (song_id,))
        c.commit()
        return True

    def get_all_songs(self) -> List[SongMetadata]:
        rows = self._conn().execute("SELECT * FROM songs ORDER BY artist, title").fetchall()
        return [self._row_to_meta(r) for r in rows]

    def get_song(self, song_id: int) -> Optional[SongMetadata]:
        row = self._conn().execute("SELECT * FROM songs WHERE song_id=?", (song_id,)).fetchone()
        return self._row_to_meta(row) if row else None

    def _row_to_meta(self, r) -> SongMetadata:
        return SongMetadata(
            song_id=r['song_id'], title=r['title'], artist=r['artist'] or '',
            album=r['album'] or '', year=r['year'] or '',
            duration=r['duration'] or 0.0, genre=r['genre'] or '',
            file_path=r['file_path'] or '', date_added=r['date_added'] or '',
            fingerprint_count=r['fp_count'] or 0,
            cover_art_path=r['cover_art'] or '', tags=r['tags'] or ''
        )

    def get_stats(self) -> Dict[str, Any]:
        c       = self._conn()
        n_songs = c.execute("SELECT COUNT(*) FROM songs").fetchone()[0]
        n_fps   = c.execute("SELECT COUNT(*) FROM fingerprints").fetchone()[0]
        n_hist  = c.execute("SELECT COUNT(*) FROM history").fetchone()[0]
        size_mb = round(os.path.getsize(self.db_path) / (1024 * 1024), 2) \
                  if os.path.exists(self.db_path) else 0
        return {'total_songs': n_songs, 'total_fingerprints': n_fps,
                'total_history': n_hist, 'db_size_mb': size_mb, 'db_path': self.db_path}

    # ── History ──────────────────────────────────────────────────────────────

    def add_history_entry(self, success: bool, song_id: Optional[int], confidence: float, mode: str):
        c = self._conn()
        c.execute(
            "INSERT INTO history (success, song_id, confidence, mode) VALUES (?,?,?,?)",
            (1 if success else 0, song_id, confidence, mode)
        )
        c.commit()

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        rows = self._conn().execute(f"""
            SELECT h.*, s.title, s.artist 
            FROM history h 
            LEFT JOIN songs s ON h.song_id = s.song_id 
            ORDER BY h.timestamp DESC LIMIT {limit}
        """).fetchall()
        return [dict(r) for r in rows]

    # ── Matching ──────────────────────────────────────────────────────────────

    def query(
        self,
        fingerprints: List[Tuple[str, int]],
        topn: int = 5,
        min_confidence: float = 0.10
    ) -> List[MatchResult]:
        """Offset-histogram matching (same method as Shazam)."""
        if not fingerprints:
            return []

        c            = self._conn()
        query_hashes = {h: t for h, t in fingerprints}
        hash_list    = list(set(query_hashes.keys()))

        offsets_by_song: Dict[int, Counter] = defaultdict(Counter)
        
        # Chunk queries to avoid SQLite parameter limit (usually 999)
        chunk_size = 900
        for i in range(0, len(hash_list), chunk_size):
            chunk = hash_list[i : i + chunk_size]
            placeholders = ','.join(['?'] * len(chunk))
            rows = c.execute(
                f"SELECT hash, time_offset, song_id FROM fingerprints WHERE hash IN ({placeholders})",
                chunk
            ).fetchall()
            
            for row in rows:
                h, db_t, sid = row['hash'], row['time_offset'], row['song_id']
                if h in query_hashes:
                    offsets_by_song[sid][db_t - query_hashes[h]] += 1

        if not offsets_by_song:
            return []

        # most_common(1)[0] returns (offset_delta, hit_count)
        scores = {
            sid: counter.most_common(1)[0]
            for sid, counter in offsets_by_song.items()
        }
        # Sort by hit_count (index [1]), NOT offset_delta (index [0])
        sorted_songs = sorted(scores.items(), key=lambda x: x[1][1], reverse=True)
        max_score    = sorted_songs[0][1][1]

        from core.fingerprint import HOP_SIZE, SAMPLE_RATE
        results = []
        for sid, (best_offset, count) in sorted_songs[:topn]:
            conf = min(count / max(len(fingerprints) * 0.15, 1), 1.0)
            if conf < min_confidence:
                continue
            song = self.get_song(sid)
            if not song:
                continue
            offset_s = max(0.0, best_offset * HOP_SIZE / SAMPLE_RATE)
            results.append(MatchResult(
                song_id=sid, title=song.title, artist=song.artist,
                album=song.album, year=song.year, genre=song.genre,
                confidence=conf, match_count=count, offset_seconds=round(offset_s, 2),
                is_mashup_component=False, cover_art_path=song.cover_art_path
            ))
        return results


# ─── Mashup Detector ─────────────────────────────────────────────────────────

class MashupDetector:
    """Sliding-window analysis to identify multiple songs in a mashup."""

    def __init__(self, db: SongDatabase):
        self.db = db

    def analyze(
        self,
        audio: np.ndarray,
        sr: int,
        window_sec: float = 6.0, # Shorter window for better resolution
        hop_sec: float = 3.0,
        min_confidence: float = 0.10, # Slightly lower threshold for noisy segments
        progress_cb=None,
        is_cancelled=None
    ) -> Dict[str, Any]:
        from core.fingerprint import fingerprint_audio

        total_dur   = len(audio) / sr
        # Use noise reduction for the full track
        full_fps    = fingerprint_audio(audio, sr, apply_noise_reduction=True)
        full_matches = self.db.query(full_fps, topn=10)

        n_windows = max(1, int((total_dur - window_sec) / hop_sec) + 1)
        timeline  = []

        for i in range(n_windows):
            if is_cancelled and is_cancelled():
                break
            start  = i * hop_sec
            end    = min(start + window_sec, total_dur)
            if end - start < 2.0:
                break
            seg    = audio[int(start * sr): int(end * sr)]
            # Enable noise reduction for segments to handle non-stationary noise (club environments)
            fps    = fingerprint_audio(seg, sr, apply_noise_reduction=True)
            hits   = self.db.query(fps, topn=2, min_confidence=min_confidence)
            if hits:
                b = hits[0]
                timeline.append({
                    'start': start, 'end': end,
                    'song_id': b.song_id, 'title': b.title,
                    'artist': b.artist, 'confidence': b.confidence
                })
            if progress_cb:
                progress_cb(int((i + 1) / n_windows * 100))

        consolidated  = self._consolidate(timeline)
        unique_songs  = set(s['song_id'] for s in consolidated)
        is_mashup     = len(unique_songs) > 1

        for m in full_matches:
            m.is_mashup_component = is_mashup
            for seg in consolidated:
                if seg['song_id'] == m.song_id:
                    m.mashup_segment_start = seg['start']
                    m.mashup_segment_end   = seg['end']
                    break

        # Ensure all songs from timeline are in matches
        match_ids = {m.song_id for m in full_matches}
        for seg in consolidated:
            if seg['song_id'] not in match_ids:
                song = self.db.get_song(seg['song_id'])
                if song:
                    m = MatchResult(
                        song_id=seg['song_id'], title=seg['title'], artist=seg['artist'],
                        album=song.album, year=song.year, genre=song.genre,
                        confidence=seg['confidence'], match_count=0, offset_seconds=0,
                        is_mashup_component=True, cover_art_path=song.cover_art_path,
                        mashup_segment_start=seg['start'], mashup_segment_end=seg['end']
                    )
                    full_matches.append(m)
                    match_ids.add(m.song_id)

        return {
            'is_mashup': is_mashup,
            'total_duration': total_dur,
            'matches': full_matches,
            'timeline': consolidated,
            'unique_songs': len(unique_songs)
        }

    def _consolidate(self, timeline: list) -> list:
        if not timeline:
            return []
        out, cur = [], dict(timeline[0])
        for seg in timeline[1:]:
            if seg['song_id'] == cur['song_id']:
                cur['end']        = seg['end']
                cur['confidence'] = max(cur['confidence'], seg['confidence'])
            else:
                out.append(cur)
                cur = dict(seg)
        out.append(cur)
        return out
