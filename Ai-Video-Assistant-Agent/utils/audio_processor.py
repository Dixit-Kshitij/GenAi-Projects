import os
import platform
if platform.system() == "Windows":
    os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\ffmpeg-8.1.2-essentials_build\bin"

from pydub import AudioSegment
import yt_dlp

if platform.system() == "Windows":
    AudioSegment.converter = r"C:\ffmpeg\ffmpeg-8.1.2-essentials_build\bin\ffmpeg.exe"

download_dir = "downloads"
os.makedirs(download_dir, exist_ok=True)

def download_youtube_audio(url: str) -> str:
    output_path = os.path.join(download_dir, "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_path,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }
        ],
        "extractor_args": {
            "youtube": {
                "player_client": ["android"]
            }
        },
        "quiet": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = os.path.splitext(ydl.prepare_filename(info))[0] + ".wav"

    return filename

# data = download_youtube_audio("https://youtu.be/7qZH3D7u-z8")

def convert_to_wav(input_path: str) -> str:
    """Convert any audio/video file to WAV format using pydub."""

    output_path = os.path.splitext(input_path)[0] + "_converted.wav"

    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)

    audio.export(output_path, format="wav")

    return output_path

# df = convert_to_wav(data)
# print(df)

def chunk_audio(wav_path : str , chunk_minutes : int = 10) -> list:
    audio = AudioSegment.from_wav(wav_path)
    chunk_ms = chunk_minutes * 60 * 1000
    chunks = []
    for i,start in enumerate(range(0,len(audio),chunk_ms)):
        chunk = audio[start:start + chunk_ms]
        chunk_path = f"{wav_path}_chunk{i}.wav"
        chunk.export(chunk_path , format = "wav")
        chunks.append(chunk_path)

    return chunks

# print(chunk_audio((df)))

def process_input(source: str) -> list:
    wav_path=""
    if source.startswith("http://") or source.startswith("https://"):
        print("Detected URL. downloading audio..")
        wav_path=download_youtube_audio(source)
        wav_path=convert_to_wav(wav_path)
    else:
        print("Detected local file. converting to wav..")
        wav_path = convert_to_wav(source)
    print("chunking audio")
    chunked_audio = chunk_audio(wav_path)
    print(f"Audio ready for transcription of {len(chunked_audio)}")
    return chunked_audio
