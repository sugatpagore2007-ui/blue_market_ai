from __future__ import annotations
import threading
import queue
import time

class VoiceSpeaker:
    """Offline TTS speaker with a simple queue and interrupt support.
    Uses pyttsx3 if installed. If not installed, it silently prints only.
    """
    def __init__(self, enabled: bool = True, rate: int = 170, volume: float = 1.0):
        self.enabled = enabled
        self.rate = rate
        self.volume = volume
        self.q: queue.Queue[str | None] = queue.Queue()
        self._stop_now = threading.Event()
        self._worker = threading.Thread(target=self._loop, daemon=True)
        self._worker.start()

    def say(self, text: str, block: bool = False):
        text = (text or '').strip()
        if not text:
            return
        if not self.enabled:
            return
        self.q.put(text)
        if block:
            self.q.join()

    def interrupt(self):
        """Clear pending speech and ask current speech engine to stop."""
        self._stop_now.set()
        while not self.q.empty():
            try:
                self.q.get_nowait()
                self.q.task_done()
            except Exception:
                break

    def close(self):
        self.q.put(None)

    def _loop(self):
        while True:
            text = self.q.get()
            if text is None:
                self.q.task_done(); break
            try:
                self._speak_pyttsx3(text)
            except Exception:
                # TTS failure must never crash the trading app.
                pass
            self.q.task_done()

    def _speak_pyttsx3(self, text: str):
        import pyttsx3
        self._stop_now.clear()
        engine = pyttsx3.init()
        engine.setProperty('rate', self.rate)
        engine.setProperty('volume', self.volume)
        # pyttsx3 cannot be perfectly interrupted on every Windows driver, but stop() works on most.
        def watch_stop():
            while not self._stop_now.is_set():
                time.sleep(0.05)
            try:
                engine.stop()
            except Exception:
                pass
        watcher = threading.Thread(target=watch_stop, daemon=True)
        watcher.start()
        engine.say(text)
        engine.runAndWait()
        try:
            engine.stop()
        except Exception:
            pass

speaker = VoiceSpeaker(enabled=True)

def speak(text: str, block: bool = False):
    speaker.say(text, block=block)

def interrupt_speech():
    speaker.interrupt()
