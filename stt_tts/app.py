from flask import Flask, render_template, request, send_file
import os
import requests
from dotenv import load_dotenv
from deepgram import DeepgramClient, PrerecordedOptions, FileSource

app = Flask(__name__, static_url_path='/static', static_folder='output')

# Load environment variables
load_dotenv()
DEEPGRAM_API_KEY = "0aafc758d910ac0acf4edd30ca35dfe3f397271c"
ELEVENLABS_API_KEY = "sk_cf661695b41d2d29005b18c6ab256c4a444c6362a936f92b"

@app.route('/')
def index():
    return render_template('index.html')

# Route to upload audio and transcribe using Deepgram
@app.route('/upload', methods=['POST'])
def upload():
    if 'audiofile' not in request.files:
        return "No file part"
    
    audiofile = request.files['audiofile']

    # Save audio file temporarily
    audio_path = os.path.join("uploads", audiofile.filename)
    audiofile.save(audio_path)

    # Transcribe the audio using Deepgram API
    deepgram = DeepgramClient(DEEPGRAM_API_KEY)

    with open(audio_path, "rb") as file:
        buffer_data = file.read()

    payload: FileSource = {
        "buffer": buffer_data,
    }

    options = PrerecordedOptions(model="nova-2", smart_format=True)
    response = deepgram.listen.rest.v("1").transcribe_file(payload, options)
    
    transcript = response['results']['channels'][0]['alternatives'][0]['transcript']

    # Get available voices from ElevenLabs
    url = "https://api.elevenlabs.io/v1/voices"
    headers = {"accept": "application/json", "xi-api-key": ELEVENLABS_API_KEY}
    voice_response = requests.get(url, headers=headers)
    voices = voice_response.json()['voices']

    return render_template('select_voice.html', transcript=transcript, voices=voices)


# Route to convert text to speech
@app.route('/convert', methods=['POST'])
def convert():
    transcript = request.form['transcript']
    voice_id = request.form['voice_id']

    # ElevenLabs TTS API call
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }

    data = {
        "text": transcript,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

    response = requests.post(url, json=data, headers=headers)

    # Save the audio file
    audio_output_path = os.path.join("output", "output.mp3")
    with open(audio_output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    # Render a template to play the audio file and provide a download option
    return render_template('play_audio.html', audio_file='output.mp3')


@app.route('/play_sample/<voice_id>')
def play_sample(voice_id):
    # Create a sample text to generate the audio
    sample_text = "Hello, this is a sample of my voice."

    # ElevenLabs TTS API call
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }

    data = {
        "text": sample_text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.5
        }
    }

    response = requests.post(url, json=data, headers=headers)

    # Serve the audio file directly to the audio player without saving it
    return response.content, 200, {'Content-Type': 'audio/mpeg'}


if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    app.run(debug=True)
