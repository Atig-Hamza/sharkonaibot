"""
Skill: Audio Transcription
Convert voice messages / audio files to text.
"""

import asyncio
import os
import subprocess

from config import CONFIG
from logger import log
from skills.system_commands import ToolResult


SKILL_DEFINITIONS = [
    {
        "name": "transcribe_audio",
        "description": (
            "Transcribe an audio file to text using speech recognition. "
            "Supports OGG, WAV, MP3, M4A, FLAC, WebM. "
            "Uses Google Web Speech API (free, no key needed)."
        ),
        "parameters": {
            "audio_path": {"type": "string", "description": "Path to the audio file."},
            "language": {"type": "string", "description": "Language code (default: 'en-US'). Examples: 'fr-FR', 'ar-SA', 'es-ES'."},
        },
    },
]


def _convert_audio_to_wav(input_path: str) -> str:
    wav_path = os.path.splitext(input_path)[0] + "_converted.wav"
    try:
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1", "-sample_fmt", "s16", wav_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and os.path.exists(wav_path):
            return wav_path
    except FileNotFoundError:
        pass
    except Exception as e:
        log.warning(f"ffmpeg error: {e}")
    try:
        py_convert = (
            f"import subprocess, sys; "
            f"subprocess.run([sys.executable, '-m', 'pip', 'install', 'pydub'], capture_output=True); "
            f"from pydub import AudioSegment; "
            f"audio = AudioSegment.from_file(r'{input_path}'); "
            f"audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2); "
            f"audio.export(r'{wav_path}', format='wav')"
        )
        result = subprocess.run(["python", "-c", py_convert], capture_output=True, text=True, timeout=60)
        if result.returncode == 0 and os.path.exists(wav_path):
            return wav_path
    except Exception as e:
        log.warning(f"Fallback conversion error: {e}")
    return ""


def _transcribe_with_speech_recognition(wav_path: str, language: str = "en-US") -> str:
    try:
        import speech_recognition as sr
    except ImportError:
        subprocess.run(["pip", "install", "SpeechRecognition"], capture_output=True, timeout=60)
        import speech_recognition as sr
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300
    recognizer.dynamic_energy_threshold = True
    with sr.AudioFile(wav_path) as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        audio_data = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio_data, language=language)
    except sr.UnknownValueError:
        pass
    except sr.RequestError as e:
        log.warning(f"Google Speech API error: {e}")
    return ""


def _transcribe_powershell_fallback(wav_path: str) -> str:
    ps_script = f"""
try {{
    Add-Type -AssemblyName System.Speech
    $recognizer = New-Object System.Speech.Recognition.SpeechRecognitionEngine
    $recognizer.SetInputToWaveFile("{wav_path.replace(chr(92), chr(92)*2)}")
    $grammar = New-Object System.Speech.Recognition.DictationGrammar
    $recognizer.LoadGrammar($grammar)
    $result = $recognizer.Recognize()
    if ($result) {{ Write-Output $result.Text }} else {{ Write-Error "No speech recognized"; exit 1 }}
    $recognizer.Dispose()
}} catch {{ Write-Error $_.Exception.Message; exit 1 }}
"""
    try:
        proc = subprocess.run(
            ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return ""


async def transcribe_audio(audio_path: str, language: str = "auto") -> ToolResult:
    log.info(f"Transcribing audio: {audio_path} (language: {language})")
    if not os.path.exists(audio_path):
        return ToolResult(success=False, stdout="", stderr=f"Audio file not found: {audio_path}", return_code=1)
    loop = asyncio.get_event_loop()
    ext = os.path.splitext(audio_path)[1].lower()
    if ext == ".wav":
        wav_path = audio_path
    else:
        wav_path = await loop.run_in_executor(None, _convert_audio_to_wav, audio_path)
        if not wav_path:
            return ToolResult(success=False, stdout="", stderr=f"Failed to convert {ext} to WAV.", return_code=1)
    try:
        if language == "auto":
            languages_to_try = list(CONFIG.VOICE_LANGUAGES)
        else:
            languages_to_try = [language]
        best_text = ""
        best_lang = ""
        for lang in languages_to_try:
            text = await loop.run_in_executor(None, _transcribe_with_speech_recognition, wav_path, lang)
            if text and len(text.strip()) > 0:
                words = text.lower().split()
                unique_words = set(words)
                repetition_ratio = len(unique_words) / max(len(words), 1)
                if repetition_ratio > 0.2 or len(words) <= 3:
                    best_text = text
                    best_lang = lang
                    break
                elif not best_text:
                    best_text = text
                    best_lang = lang
        if not best_text:
            text = await loop.run_in_executor(None, _transcribe_powershell_fallback, wav_path)
            if text:
                best_text = text
                best_lang = "en-US (Windows)"
        if best_text:
            lang_info = f" [{best_lang}]" if best_lang else ""
            return ToolResult(success=True, stdout=f"🎤 Transcription{lang_info}:\n{best_text}", stderr="", return_code=0)
        tried = ", ".join(languages_to_try)
        return ToolResult(success=False, stdout="", stderr=f"Could not transcribe. Tried: {tried}", return_code=1)
    finally:
        if wav_path != audio_path:
            try:
                os.remove(wav_path)
            except OSError:
                pass


SKILL_MAP = {
    "transcribe_audio": transcribe_audio,
}
