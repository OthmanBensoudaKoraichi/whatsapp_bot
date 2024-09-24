from ppadb.client import Client as AdbClient
import subprocess
import time
import threading
import speech_recognition as sr
import openai
from pydub import AudioSegment
from pydub.utils import which
import os

# Replace 'your-api-key' with your actual OpenAI API key
openai.api_key = 'your-api-key'

# Ensure pydub uses ffmpeg
AudioSegment.converter = which("ffmpeg")

# Connect to ADB server
client = AdbClient(host="127.0.0.1", port=5037)
devices = client.devices()

if len(devices) == 0:
    print("No devices connected")
    exit()

device = devices[0]

summaries = {}


def is_call_active():
    result = subprocess.run(['adb', 'shell', 'dumpsys', 'telephony.registry'], stdout=subprocess.PIPE)
    output = result.stdout.decode('utf-8')
    return 'mCallState=2' in output  # 2 indicates the call is active, 0 is idle


def start_recording(call_index):
    # Start screen recording using an app
    subprocess.Popen(['adb', 'shell', 'screenrecord', f'/sdcard/call_recording_{call_index}.mp4'])


def stop_recording(call_index):
    # Stop recording by interrupting the screenrecord command
    subprocess.run(['adb', 'shell', 'pkill', '-INT', 'screenrecord'])

    # Define paths
    mp4_path = f'./call_recording_{call_index}.mp4'

    # Pull the recorded file from the device
    result = subprocess.run(['adb', 'pull', f'/sdcard/call_recording_{call_index}.mp4', mp4_path], capture_output=True,
                            text=True)
    if result.returncode != 0:
        print(f"Error pulling recording {call_index}: {result.stderr}")
        return

    # Check if the file exists and is valid
    if not os.path.exists(mp4_path) or os.path.getsize(mp4_path) == 0:
        print(f"Recording file {mp4_path} does not exist or is empty.")
        return


def convert_speech_to_text(audio_file):
    recognizer = sr.Recognizer()
    with sr.AudioFile(audio_file) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        return "Speech recognition could not understand audio"
    except sr.RequestError as e:
        return f"Could not request results from the speech recognition service; {e}"


def summarize_text(text):
    response = openai.Completion.create(
        engine="davinci",  # You can use "gpt-3.5-turbo" or another model if preferred
        prompt=f"Cet entretien téléphonique contient du Français et/ou de la Darija Marocaine. Résume le, en indiquant si le client est susceptible de souscrire un contrat d'assurance:\n\n{text}\n\nRésumé:",
        max_tokens=150,
        n=1,
        stop=None,
        temperature=0.7,
    )
    summary = response.choices[0].text.strip()
    return summary


def process_recording(call_index, number):
    mp4_path = f'./call_recording_{call_index}.mp4'

    # Here you could add code to handle the MP4 file if needed
    # For example, extracting audio from the MP4 file or processing the video

    print(f"Processing recording of call with {number} at {mp4_path}")
    # Dummy transcription and summary since we are not converting audio
    transcription = "Dummy transcription for call recording."
    summary = "Dummy summary for call recording."

    summaries[number] = summary

    with open(f'summary_{number}.txt', 'w') as f:
        f.write(summary)


def call_numbers(numbers):
    call_index = 0
    for number in numbers:
        call_index += 1
        print(f"Dialing {number}...")
        call_command = f"am start -a android.intent.action.CALL -d tel:{number}"
        device.shell(call_command)

        start_recording(call_index)

        call_active = False
        while True:
            if is_call_active():
                if not call_active:
                    print("Call started")
                    call_active = True
            else:
                if call_active:
                    print("Call ended")
                    call_active = False
                    break
            time.sleep(1)

        stop_recording(call_index)
        print(f"Call with {number} recorded and ended")

        threading.Thread(target=process_recording, args=(call_index, number)).start()


numbers = ['+212708958359']
call_numbers(numbers)

for number, summary in summaries.items():
    print(f"Summary for {number}: {summary}")
