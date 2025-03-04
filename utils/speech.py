import numpy as np
import torch
import queue
import threading
import time
import pyaudio
from faster_whisper import WhisperModel
from agent import run 
import string

model = WhisperModel("small", device="cuda" if torch.cuda.is_available() else "cpu", compute_type="float32")


FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024
SILENCE_TIME = 2  # how long it waits to process a command

audio_queue = queue.Queue()

last_command = None  

def audio_callback(in_data, frame_count, time_info, status):
    """Callback function to receive audio data."""
    audio_queue.put(in_data)
    return (in_data, pyaudio.paContinue)

def is_silent(audio_buffer, threshold=300):
    """Detects if audio contains only silence based on amplitude threshold."""
    audio_np = np.frombuffer(audio_buffer, dtype=np.int16)
    return np.abs(audio_np).mean() < threshold 

def get_speech_command():
    """Listens for a single speech command, transcribes it, and returns the extracted text."""
    print("🎤 Listening for 'Hey Flow'...")

    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True,
                    frames_per_buffer=CHUNK, stream_callback=audio_callback)
    stream.start_stream()

    audio_buffer = b""
    last_speech_time = None

    try:
        while True:
            while not audio_queue.empty():
                audio_chunk = audio_queue.get()
                audio_buffer += audio_chunk

                if not is_silent(audio_chunk):  
                    last_speech_time = time.time() 

            if last_speech_time and time.time() - last_speech_time > SILENCE_TIME:
                break #only process when we talk and stop

        if not audio_buffer:  # no talking
            print("🔇 No speech detected.")
            return None

        print("⏳ Silence detected, processing speech...")

        audio_np = np.frombuffer(audio_buffer, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = model.transcribe(audio_np, language="en", beam_size=5)
        full_transcript = " ".join(segment.text.strip() for segment in segments).strip()

        if not full_transcript:
            print("🔇 No speech detected.")
            return None

        print(f"🗣️ Detected speech: {full_transcript}")

        trigger_phrases = ["hey flow", "hey flo", "hello flow", "ay flow"]
        command = None

        for phrase in trigger_phrases:
            index = full_transcript.lower().translate(str.maketrans("", "", string.punctuation)).find(phrase.lower())
            if index != -1:
                command = full_transcript[index + len(phrase):].strip()
                break

        if command:
            print(f"➡️ Running command: {command}")
            return command
        else:
            print("🔇 'Hey Flow' detected but no valid command extracted.")
            return None

    except Exception as e:
        print(f"❌ Error in speech processing: {e}")
        return None

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()