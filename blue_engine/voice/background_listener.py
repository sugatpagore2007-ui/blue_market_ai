from __future__ import annotations

"""Phase 15.6 always-on background voice listener.

This module lets Blue listen in the background while the terminal keeps accepting
normal typed commands. It is intentionally conservative:
- It never uses typed fallback inside the background worker, so it cannot steal
  the terminal input() prompt.
- It executes commands only when a wake phrase is heard, or when the phrase is a
  clear Blue command such as "check gold", "best", "train your brain".
- It can be started/stopped safely from the command shell.
"""

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

from voice.voice_loop import listen_once_no_text, voice_backend_status
from voice.speaker import speak, interrupt_speech


CommandHandler = Callable[..., Optional[str]]

WAKE_WORDS = (
    "hey blue", "ok blue", "okay blue", "hello blue", "hi blue", "blue",
    "hey google", "ok google", "okay google", "hey siri", "alexa",
)

DIRECT_COMMAND_STARTS = (
    # Core commands from the friendly command guide. Keep these stable for text + voice.
    "help", "show commands", "show simple commands", "list commands", "start", "status",
    "stop", "stop everything", "exit", "close blue",

    # Market analysis.
    "gold", "xau", "xauusd", "btc", "bitcoin", "eur", "euro", "gbp", "pound", "jpy", "yen",
    "check", "tell me", "show me", "show my", "why", "take out", "news", "macro", "scan", "best",

    # Learning / reports.
    "learn", "train", "brain", "ml", "memory", "history", "mt5 learn", "backtest",
    "internet", "web", "environment", "baby brain", "newborn brain",

    # Broker / account / management.
    "connect", "use", "broker", "account", "balance", "risk", "lot", "trades", "open trades",
    "profit", "stats", "statistics", "journal", "move", "breakeven", "break even", "be ",
    "trail", "close", "manager", "autopilot", "pyramid", "pyramiding", "order doctor",

    # Voice / UI / vision / auto controls.
    "voice", "talk", "voice text", "text voice", "dual mode", "parallel mode", "both mode",
    "quiet", "screenshot", "ocr", "candles", "patterns", "full auto", "auto now",
)

STOP_LISTENER_COMMANDS = {
    "voice off", "stop voice", "stop listening", "listening off", "microphone off",
}

INTERRUPT_COMMANDS = {
    "quiet", "stop speaking", "interrupt", "silence", "be quiet", "shut up",
}


def _clean(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


def extract_command_from_heard(heard: str) -> str:
    """Return command text if a heard phrase should be executed, else ''."""
    text = _clean(heard)
    if not text:
        return ""

    # Wake-word mode: "hey blue check gold" -> "check gold".
    for wake in sorted(WAKE_WORDS, key=len, reverse=True):
        if text == wake:
            return "help"
        if text.startswith(wake + " "):
            return text[len(wake):].strip()

    # Natural direct commands still work, so user is not forced to say Blue every time.
    if text.startswith(DIRECT_COMMAND_STARTS):
        return text

    return ""


@dataclass
class BackgroundVoiceState:
    enabled: bool = False
    last_heard: str = ""
    last_command: str = ""
    last_error: str = ""
    commands_executed: int = 0


class BackgroundVoiceController:
    def __init__(self):
        self.state = BackgroundVoiceState()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._handler: Optional[CommandHandler] = None
        self._print_fn = print
        self._lock = threading.Lock()

    def start(self, command_handler: CommandHandler, print_fn=print, speak_ready: bool = False):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return {"ok": True, "message": "Background voice listener already running."}

            status = voice_backend_status()
            if not (status.speech_recognition and (status.pyaudio or (status.sounddevice and status.numpy))):
                self.state.enabled = False
                self.state.last_error = "Mic backend not ready. Type voice status / voice install help."
                return {"ok": False, "message": self.state.last_error}

            self._handler = command_handler
            self._print_fn = print_fn
            self._stop_event.clear()
            self.state = BackgroundVoiceState(enabled=True)
            self._thread = threading.Thread(target=self._loop, name="BlueBackgroundVoice", daemon=True)
            self._thread.start()
            msg = "Background voice listener started. You can type while Blue listens. Say: 'hey blue check gold' or just 'check gold'."
            if speak_ready:
                speak("Background voice is active.", block=False)
            return {"ok": True, "message": msg}

    def stop(self):
        with self._lock:
            self._stop_event.set()
            self.state.enabled = False
            return {"ok": True, "message": "Background voice listener stopped."}

    def status_text(self) -> str:
        thread_alive = bool(self._thread and self._thread.is_alive())
        mic = voice_backend_status().as_text()
        return (
            "BACKGROUND VOICE LISTENER\n"
            f"Running           : {thread_alive}\n"
            f"Enabled           : {self.state.enabled}\n"
            f"Commands executed : {self.state.commands_executed}\n"
            f"Last heard        : {self.state.last_heard or 'n/a'}\n"
            f"Last command      : {self.state.last_command or 'n/a'}\n"
            f"Last error        : {self.state.last_error or 'n/a'}\n\n"
            "Wake examples:\n"
            "- hey blue check gold\n"
            "- blue show me best trade\n"
            "- hey blue train your brain\n\n"
            "Direct examples also work:\n"
            "- check gold\n"
            "- show my open trades\n"
            "- take out win rate of btc\n"
            "- stop everything\n\n"
            + mic
        )

    def _loop(self):
        self._print_fn("Background voice: active. Type commands normally; voice is listening too.")
        while not self._stop_event.is_set():
            try:
                heard = listen_once_no_text(silent=True)
                if self._stop_event.is_set():
                    break
                heard = _clean(heard)
                if not heard:
                    continue
                self.state.last_heard = heard
                cmd = extract_command_from_heard(heard)
                if not cmd:
                    continue
                self.state.last_command = cmd
                if cmd in STOP_LISTENER_COMMANDS:
                    self._print_fn("\nVoice command: stop background voice")
                    speak("Voice listener stopped.", block=False)
                    self.stop()
                    break
                if cmd in INTERRUPT_COMMANDS:
                    interrupt_speech()
                    self._print_fn("\nVoice command: speech interrupted")
                    continue
                self.state.commands_executed += 1
                self._print_fn(f"\nVoice command understood: {cmd}")
                handler = self._handler
                if handler:
                    response = handler(cmd, from_voice=True)
                    if response:
                        speak(str(response), block=False)
            except Exception as exc:
                self.state.last_error = str(exc)
                # Avoid a tight error loop if audio device fails.
                time.sleep(2)


controller = BackgroundVoiceController()


def start_background_voice(command_handler: CommandHandler, print_fn=print, speak_ready: bool = False):
    return controller.start(command_handler, print_fn=print_fn, speak_ready=speak_ready)


def stop_background_voice():
    return controller.stop()


def background_voice_status_text() -> str:
    return controller.status_text()
