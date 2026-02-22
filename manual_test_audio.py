
import numpy as np
from core.audio import save_wav, SAMPLE_RATE
from core.engine import MashupIDEngine

def create_test_assets():
    print("Generating synthetic test audio...")
    duration = 60.0
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    # A multi-frequency signal to make fingerprinting more interesting
    audio = 0.5 * np.sin(2 * np.pi * 440 * t) + 0.3 * np.sin(2 * np.pi * 880 * t)
    
    save_wav("test_song.wav", audio, SAMPLE_RATE)
    
    # Query is just a segment (offset by 2 seconds)
    query = audio[int(2 * SAMPLE_RATE):int(7 * SAMPLE_RATE)]
    save_wav("query.wav", query, SAMPLE_RATE)
    print("Created test_song.wav and query.wav")

def test_engine():
    e = MashupIDEngine()
    print("Indexing test song...")
    res = e.index_song_file("test_song.wav", title="Test Song", artist="Antigravity AI")
    print(f"Index result: {res}")
    
    print("\nIdentifying query clip...")
    # Mimic file identification behavior
    import os
    results = e.db.query(None) # Just checking if we can get results
    
    from core.audio import load_audio_file
    from core.fingerprint import fingerprint_audio
    
    q_audio, q_sr = load_audio_file("query.wav", SAMPLE_RATE)
    q_fps = fingerprint_audio(q_audio, q_sr)
    
    matches = e.db.query(q_fps)
    
    print(f"Found {len(matches)} matches")
    for m in matches:
        print(f"  - {m.title} by {m.artist} (Conf: {m.confidence*100:.1f}%)")

if __name__ == "__main__":
    create_test_assets()
    test_engine()
