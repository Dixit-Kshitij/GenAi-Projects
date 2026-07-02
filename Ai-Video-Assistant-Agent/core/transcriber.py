import whisper
import os
from dotenv import load_dotenv
load_dotenv()
WHISPER_MODEL = whisper.load_model("base")
SARVAM_API_MODEL = os.getenv("")
_model = None

def load_model():
  global _model

  if _model == None:
    print("Model is loading...")
    _model = whisper.load_model("base")
    print("whisper model loaded successfully")
    
  return _model

def transcribe_chunks(chunk_path: str,translate: bool = False) -> str:

  model = load_model()

  task = "translate" if translate else "transcribe"

  result = model.transcribe(chunk_path,task = task)

  return result["text"]

def transcribe_all(chunks : list , translate :bool = False) -> str:

  transcriptions = []

  for chunk in chunks:
    transcription = transcribe_chunks(chunk,translate)
    transcriptions.append(transcription)

  print("transcriptions completed")

  return " ".join(transcriptions)

