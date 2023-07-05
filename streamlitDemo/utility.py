import streamlit as st
import requests
from pydub import AudioSegment
import os
import tempfile
from pathlib import Path
from streamlit_webrtc import WebRtcMode, webrtc_streamer
import queue
import base64
import json

# VIDEO PATHS
DEMO_VIDEO_1_PATH = './assets/video/video1.mp4'
DEMO_VIDEO_2_PATH  = './assets/video/video2.mp4'
DEMO_VIDEO_3_PATH  = './assets/video/video3.mp4'

# AUDIO PATHS
DEMO_AUDIO_1_PATH  = './assets/audio/audio_video1.mp3'
DEMO_AUDIO_2_PATH  = './assets/audio/audio_video2.mp3'
DEMO_AUDIO_3_PATH  = './assets/audio/audio_video3.mp3'

# API ENDPOINTS
STT_API_KEY = 'STT_API'
QA_API_KEY = 'QA_API'
TTS_API_KEY = 'TTS_API'
NO_API_SET_FLAG = '-1'

# QA RIDDLE VALUES
QA_QUESTION_BANK = {
    "riddle1": "there is really nothing improper about me,i am just a fraction,my numerator exceeds my denominator,i am not a mixed fraction or mixed number,an example of me is 7 3",
    "riddle2": "I am a point of concurrency associated with a triangle. I am a meeting point of three lines associated with a triangle. I am in a way a center of some sort. I am not the in-center and neither am I the circum-center. I am the point at which the three altitudes of a triangle meet. Who am I?",
    "riddle3": "I am a theorem in mechanics That is named after a French scientist named Bernard. I apply to the equilibrium state of an object. I give the relationship between three coplanar concurrent forces that act on a body in equilibrium. I recall the sine rule. Who am I?"
    }

# TTS VOICE OPTIONS
TTS_VOICE_BANK = {
    "voice1": "Ghanaian (Voice 1)",
    "voice2": "Ghanaian (Voice 2)"
}

# DEFAULTS FOR REAL TIME AUDIO RECORDING TRANSCRIPTION
TIMEOUT = 3  # Timeout for getting frames from the audio receiver. Default is 3 seconds.

# API FUNCTIONS
def get_stt_transcript(audioFile):
    STT_API = get_stt_api()

    # only make the API call if a valid url is present
    if STT_API != NO_API_SET_FLAG:
        STT_TRANSCRIPT_API = STT_API.rstrip('/') + '/get-transcript'
        with open(audioFile, "rb") as audio_file:
            audio_bytes = audio_file.read()
            bytes_data = base64.b64encode(audio_bytes).decode()

            # Create payload
            payload = {"data": bytes_data, "filename": "temp_audio.wav"}
            payload = json.dumps(payload)

            # Send GET request to API endpoint
            response = requests.get(STT_TRANSCRIPT_API, data=payload)

            if response.status_code == 200:
                transcript = response.json()['transcript']
                return transcript

def get_qa_answer(question):
    QA_API = get_qa_api()

    # only make the API call if a valid url is present
    if QA_API != NO_API_SET_FLAG:
        question = json.dumps({'text' : question})
        response = requests.get(QA_API.rstrip('/') + '/answer', data=question)

        if response.status_code == 200:
            answer = response.json()['answer']
            return answer

def get_tts_audio(text, voice):
    TTS_API = get_tts_api()
    # only make the API call if a valid url is present
    if TTS_API != NO_API_SET_FLAG:
        voiceOption = '1' if voice == TTS_VOICE_BANK['voice1'] else '2'

        payload = json.dumps({'text' : text, 'voice': voiceOption})
        response = requests.get(TTS_API.rstrip('/') + '/synthesize_audios', data=payload)

        outputFileName = "tts_output.wav"

        if response.status_code == 200:
            with open(outputFileName, "wb+") as file:
                file.write(response.content)
    
    return outputFileName

# SET API IN ENVIRONMENT VARIABLES
def set_stt_api(apiVal):
    os.environ[STT_API_KEY] = apiVal

def set_qa_api(apiVal):
    os.environ[QA_API_KEY] = apiVal

def set_tts_api(apiVal):
    os.environ[TTS_API_KEY] = apiVal

# GET API IN ENVIRONMENT VARIABLES
def get_stt_api():
    return os.environ.get(STT_API_KEY, NO_API_SET_FLAG)

def get_qa_api():
    return os.environ.get(QA_API_KEY, NO_API_SET_FLAG)
    
def get_tts_api():
    return os.environ.get(TTS_API_KEY, NO_API_SET_FLAG)

# AUTOPLAY AUDIO
def autoplay_audio(audioFile):
    with open(audioFile, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio controls autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(
            md,
            unsafe_allow_html=True,
        )

# LOCAL STT PROCESSING
def realtime_audio_file_STT(audio_file_path):
    with st.spinner('Transcribing'):
        # creating a placeholder for the fixed sized textbox
        transcriptBox = st.empty()
        transcriptText = ''
        transcriptBox.text_area(
            "Real time transcription",
            transcriptText,
            label_visibility  = 'hidden'
        )

        # temp location for audio chunks
        temp_dir = tempfile.mkdtemp()
        audio_chunk_temp_file = os.path.join(temp_dir, "temp.wav")

        # majority of audio chunk code referenced from https://www.geeksforgeeks.org/audio-processing-using-pydub-and-google-speechrecognition-api/#
        
        # Input audio file to be sliced
        audio = AudioSegment.from_mp3(audio_file_path)

        # Length of the audiofile in milliseconds
        n = len(audio)

        # Interval length at which to slice the audio file.
        # If length is 22 seconds, and interval is 5 seconds,
        # The chunks created will be:
        # chunk1 : 0 - 5 seconds
        # chunk2 : 5 - 10 seconds
        # chunk3 : 10 - 15 seconds
        # chunk4 : 15 - 20 seconds
        # chunk5 : 20 - 22 seconds
        # 5seconds proved to be the best interval to make the transcription correspond to the audio which is autoplayed in the UI
        interval = 5 * 1000

        # Length of audio to overlap.
        # If length is 22 seconds, and interval is 5 seconds,
        # With overlap as 1.5 seconds,
        # The chunks created will be:
        # chunk1 : 0 - 5 seconds
        # chunk2 : 3.5 - 8.5 seconds
        # chunk3 : 7 - 12 seconds
        # chunk4 : 10.5 - 15.5 seconds
        # chunk5 : 14 - 19.5 seconds
        # chunk6 : 18 - 22 seconds
        overlap = 0

        # Initialize start and end seconds to 0
        start = 0
        end = 0
        
        # Flag to keep track of end of file.
        # When audio reaches its end, flag is set to 1 and we break
        flag = 0

        # Iterate from 0 to end of the file,
        # with increment = interval
        for i in range(0, 2 * n, interval):
            
            # During first iteration,
            # start is 0, end is the interval
            if i == 0:
                start = 0
                end = interval
        
            # All other iterations,
            # start is the previous end - overlap
            # end becomes end + interval
            else:
                start = end - overlap
                end = start + interval
        
            # When end becomes greater than the file length,
            # end is set to the file length
            # flag is set to 1 to indicate break.
            if end >= n:
                end = n
                flag = 1
        
            # Storing audio file from the defined start to end
            sound_chunk = audio[start:end]

            # Store the sliced audio file
            sound_chunk.export(audio_chunk_temp_file, format ="wav")
            
            # Slicing of the audio file is done. transcribe audio chunks
            transcriptText += get_stt_transcript(audio_chunk_temp_file)
            os.remove(audio_chunk_temp_file)

            transcriptBox.text_area("", transcriptText)

            # Check for flag.
            # If flag is 1, end of the whole audio reached.
            if flag == 1:
                break

def realtime_audio_recording_STT():
    # temp location for audio chunks
    temp_dir = tempfile.mkdtemp()
    audio_chunk_temp_file = os.path.join(temp_dir, "recording_temp.wav")

    # streamlit-webrtc component containing the audio functionality
    webrtc_ctx = webrtc_streamer(
        key="speech-to-text",
        mode=WebRtcMode.SENDONLY,
        audio_receiver_size=1024,
        media_stream_constraints={"video": False, "audio": True},
    )

    # creating a placeholder for the fixed sized textbox
    with st.spinner("Running..Say Something!"):
        transcriptBox = st.empty()
        transcriptText = ''
        transcriptBox.text_area(
            "Real time transcription",
            transcriptText,
            label_visibility  = 'hidden'
        )
    
        while webrtc_ctx.state.playing:
            if webrtc_ctx.audio_receiver:
                try:
                    audio_frames = webrtc_ctx.audio_receiver.get_frames(timeout=TIMEOUT)
                except queue.Empty:
                    continue

                sound_chunk = AudioSegment.empty()
                for audio_frame in audio_frames:
                    sound = AudioSegment(
                        data=audio_frame.to_ndarray().tobytes(),
                        sample_width=audio_frame.format.bytes,
                        frame_rate=audio_frame.sample_rate,
                        channels=len(audio_frame.layout.channels),
                    )
                    sound_chunk += sound
                
                if len(sound_chunk) > 0:
                    sound_chunk.export(audio_chunk_temp_file, format ="wav")
                    transcriptText += get_stt_transcript(audio_chunk_temp_file)
                    transcriptBox.text_area("", transcriptText)
                    os.remove(audio_chunk_temp_file)
            else:
                break

# OVERALL END TO END OPERATION DISPLAY
def ai_operation(video_file_path, audio_file_path):
    videoCol, rttCol = st.columns([3,2])

    with videoCol:
        vid1_file = open(video_file_path, 'rb')
        vid1_bytes = vid1_file.read()
        st.video(vid1_bytes)

    with rttCol:
        if st.button('Transcribe'):
            realtime_audio_file_STT(audio_file_path)

    st.divider()

    questionCol, answerCol = st.columns([1.5,1])

    with questionCol:
        st.write("#### Question")
        # st.write(QA_QUESTION["text"])
        # st.write(get_stt_text()['reference'])
        st.text_area("Question", QA_QUESTION_BANK["riddle1"], label_visibility  = 'hidden')
        
    with answerCol:
        st.write("#### Answer")
        # st.write(QA_ANSWER["answer"])
        # st.write(get_qa_answer(question))
        st.text_area("Answer", "answer", label_visibility  = 'hidden')
    
    st.divider()

    st.write('#### Generated Speech')

    # TODO: get actual audio from API and display
    audio_file = open(audio_file_path, 'rb')
    audio_bytes = audio_file.read()
    st.audio(audio_bytes, format="audio/mp3")
