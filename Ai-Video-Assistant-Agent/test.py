# English
# from utils.audio_processor import process_input
# from core.transcriber import transcribe_all

# source = "https://youtu.be/Lg-meK5IU8Q"

# chunks = process_input(source)

# print(transcribe_all(chunks))

# Hindi
from utils.audio_processor import process_input
from core.transcriber import transcribe_all

source = "https://youtu.be/tplWXd_T7YQ"

chunks = process_input(source)

print(transcribe_all(chunks))