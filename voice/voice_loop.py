from __future__ import annotations

"""Phase 15.5 Voice Control Hotfix.

Why this exists:
- SpeechRecognition's sr.Microphone needs PyAudio.
- On Python 3.14, PyAudio wheels may be unavailable on many Windows installs.
- Blue now tries multiple input backends before falling back to typing:
  1) SpeechRecognition + PyAudio microphone
  2) sounddevice + numpy recording + SpeechRecognition AudioData
  3) typed command fallback

This keeps voice mode usable even when PyAudio is missing.
"""

from dataclasses import dataclass
import importlib.util
import wave
from pathlib import Path
from typing import Optional

from voice.speaker import speak, interrupt_speech
from voice.conversation import conversation, detect_conversation_intent, answer_conversation_intent

TMP_AUDIO = Path("voice_last_input.wav")


@dataclass
class VoiceBackendStatus:
    speech_recognition: bool
    pyaudio: bool
    sounddevice: bool
    numpy: bool
    pyttsx3: bool

    def as_text(self) -> str:
        def ok(v: bool) -> str:
            return "OK" if v else "missing"
        lines = [
            "VOICE CONTROL STATUS",
            f"SpeechRecognition : {ok(self.speech_recognition)}",
            f"PyAudio           : {ok(self.pyaudio)}",
            f"sounddevice       : {ok(self.sounddevice)}",
            f"numpy             : {ok(self.numpy)}",
            f"pyttsx3 TTS       : {ok(self.pyttsx3)}",
            "",
            "Input priority:",
            "1) SpeechRecognition + PyAudio microphone",
            "2) sounddevice microphone fallback",
            "3) typed command fallback",
        ]
        if not self.pyaudio and self.sounddevice and self.numpy and self.speech_recognition:
            lines.append("\nGood: PyAudio is missing, but sounddevice fallback can still use your microphone.")
        if not self.pyaudio and not self.sounddevice:
            lines.append("\nMic packages are missing. Install voice packages or use typed command fallback.")
        return "\n".join(lines)


def _has_module(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def voice_backend_status() -> VoiceBackendStatus:
    return VoiceBackendStatus(
        speech_recognition=_has_module("speech_recognition"),
        pyaudio=_has_module("pyaudio"),
        sounddevice=_has_module("sounddevice"),
        numpy=_has_module("numpy"),
        pyttsx3=_has_module("pyttsx3"),
    )


def voice_install_help() -> str:
    return """VOICE INSTALL HELP

Recommended for your Python 3.14 setup:
python -m pip install SpeechRecognition pyttsx3 sounddevice numpy

Then run:
python main.py
voice

If you specifically want PyAudio microphone backend, use Python 3.13 or 3.12 and run:
python -m pip install PyAudio SpeechRecognition pyttsx3

Blue will still work without voice packages by asking: Type command instead >
"""


def _recognize_audio_data(audio_data, silent: bool = False):
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    try:
        return recognizer.recognize_google(audio_data).lower().strip()
    except Exception as exc:
        if not silent:
            print("Could not understand voice clearly.")
            print("Reason:", exc)
        return ""


def _listen_with_pyaudio(silent: bool = False) -> str:
    import speech_recognition as sr
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        if not silent:
            print("Listening with PyAudio... speak now.")
        recognizer.adjust_for_ambient_noise(source, duration=0.4)
        audio = recognizer.listen(source, timeout=6, phrase_time_limit=10)
    try:
        return recognizer.recognize_google(audio).lower().strip()
    except Exception as exc:
        if not silent:
            print("Could not understand voice clearly.")
            print("Reason:", exc)
        return ""


def _listen_with_sounddevice(seconds: float = 6.0, samplerate: int = 16000, silent: bool = False) -> str:
    """Record mic audio without PyAudio, then pass it to SpeechRecognition.
    This path needs: sounddevice, numpy, SpeechRecognition.
    """
    import numpy as np
    import sounddevice as sd
    import speech_recognition as sr

    if not silent:
        print(f"Listening with sounddevice fallback for {int(seconds)} seconds... speak now.")
    audio = sd.rec(int(seconds * samplerate), samplerate=samplerate, channels=1, dtype="int16")
    sd.wait()
    raw = audio.tobytes()

    # Save last audio for debugging; if recognition fails user can inspect this file.
    try:
        with wave.open(str(TMP_AUDIO), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(samplerate)
            wf.writeframes(raw)
    except Exception:
        pass

    audio_data = sr.AudioData(raw, samplerate, 2)
    return _recognize_audio_data(audio_data, silent=silent)


def listen_once() -> str:
    """Voice input with safe fallbacks.

    Returns a lower-case command string. If real mic input is unavailable, returns typed input.
    """
    status = voice_backend_status()

    # Path 1: classic SpeechRecognition microphone backend.
    if status.speech_recognition and status.pyaudio:
        try:
            return _listen_with_pyaudio(silent=False)
        except Exception as exc:
            print("PyAudio mic path failed, trying sounddevice fallback...")
            print("Reason:", exc)

    # Path 2: PyAudio-free recording fallback.
    if status.speech_recognition and status.sounddevice and status.numpy:
        try:
            return _listen_with_sounddevice(silent=False)
        except Exception as exc:
            print("sounddevice mic fallback failed.")
            print("Reason:", exc)

    # Path 3: typed fallback, so the app never gets stuck.
    print("Voice mic unavailable. Using text command instead.")
    if not status.speech_recognition:
        print("Reason: SpeechRecognition is not installed")
    elif not status.pyaudio and not (status.sounddevice and status.numpy):
        print("Reason: Could not find PyAudio, and sounddevice/numpy fallback is not ready")
    return input("Type command instead > ").lower().strip()




def listen_once_no_text(silent: bool = True) -> str:
    """Mic-only listening for background mode. Never calls input().

    This is important because background voice must not steal terminal input while
    the main thread is waiting at `Blue >`.
    """
    status = voice_backend_status()
    if status.speech_recognition and status.pyaudio:
        try:
            return _listen_with_pyaudio(silent=silent)
        except Exception as exc:
            if not silent:
                print("PyAudio mic path failed, trying sounddevice fallback...")
                print("Reason:", exc)
    if status.speech_recognition and status.sounddevice and status.numpy:
        try:
            return _listen_with_sounddevice(silent=silent)
        except Exception as exc:
            if not silent:
                print("sounddevice mic fallback failed.")
                print("Reason:", exc)
    return ""

def voice_session(command_handler):
    print("Human voice mode active. Speak naturally. No need to say Blue every time.")
    print("Examples: 'check gold', 'tell me gold buy or sell', 'why', 'train your brain', 'show trades', 'stop speaking'.")
    print("Type/say: 'voice status' to check mic packages, or 'voice install help' for install commands.")
    speak("Human voice mode active. Speak naturally. You do not need to say Blue every time.")
    while True:
        cmd = listen_once()
        if not cmd:
            continue
        print("Heard:", cmd)
        conversation.remember_user(cmd)

        if cmd in ("exit", "quit", "stop voice", "stop listening", "voice off"):
            speak("Voice session stopped.")
            break
        if cmd in ("stop speaking", "interrupt", "silence", "be quiet", "shut up", "quiet"):
            interrupt_speech()
            print("Speech interrupted.")
            continue
        if cmd in ("voice status", "mic status", "microphone status"):
            msg = voice_backend_status().as_text()
            print(msg)
            speak("Voice status checked.", block=False)
            continue
        if cmd in ("voice install help", "mic install help", "install voice"):
            msg = voice_install_help()
            print(msg)
            speak("I printed voice install commands in the terminal.", block=False)
            continue

        # Direct conversational follow-ups are answered here so they feel instant.
        intent = detect_conversation_intent(cmd)
        if intent and intent != "market_opinion":
            response = answer_conversation_intent(intent)
            if response:
                print(response)
                speak(response, block=False)
                conversation.remember_assistant(response)
                continue

        response = command_handler(cmd, from_voice=True)
        if response:
            speak(str(response), block=False)
            conversation.remember_assistant(str(response))
