
import time
import threading
from core.engine import MashupIDEngine
from core.audio import SAMPLE_RATE
import numpy as np

def test_stop_responsiveness():
    e = MashupIDEngine()
    
    # Create a long audio for analysis (30s)
    duration = 30.0
    audio = np.random.randn(int(SAMPLE_RATE * duration)).astype(np.float32)
    
    print("Starting long mashup analysis...")
    # Mode = mashup to trigger sliding window
    def _run():
        # Inject callbacks
        e.on_status(lambda s, m: print(f"Status: {s} | {m}"))
        e.on_progress(lambda p: print(f"Progress: {p}%"))
        
        # We'll use the private _analyze to test cancellation directly
        # or use identify_from_microphone which starts its own thread
        e.identify_from_microphone(duration=30, mashup_mode=True)

    _run()
    
    time.sleep(2) # Let it start recording/analyzing
    print("\nInterrupting with stop()...")
    start_time = time.time()
    e.stop()
    end_time = time.time()
    
    print(f"stop() call returned in {end_time - start_time:.4f}s")
    
    if (end_time - start_time) < 0.5:
        print("SUCCESS: stop() is non-blocking.")
    else:
        print("FAILURE: stop() blocked the thread.")

    # Wait a bit to see if background thread dies
    time.sleep(1)
    print(f"Final status: {e._status}")

if __name__ == "__main__":
    test_stop_responsiveness()
