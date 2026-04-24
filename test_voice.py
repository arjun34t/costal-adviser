import os
from tools.voice import text_to_speech

text = "അപ്പോൾ നിങ്ങളുടെ ഭാവി പദ്ധതി എന്താണ്?"
output_path = "data/test_output.wav"

success = text_to_speech(text, output_path)
print(success)

if success:
    print(f"File exists: {os.path.isfile(output_path)}")
    print(f"File size: {os.path.getsize(output_path)} bytes")
