import gradio as gr
from utils import generate_script, generate_audio, truncate_text, extract_text_from_url
from prompts import SYSTEM_PROMPT
from pydub import AudioSegment
import pypdf
import os
import tempfile

def generate_podcast(file, url, tone, length):
    try:
        if file and url:
            return None, "Please provide either a PDF file or a URL, not both."
        
        if file:
            if not file.name.lower().endswith('.pdf'):
                return None, "Please upload a PDF file."
            
            pdf_reader = pypdf.PdfReader(file.name)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
        elif url:
            text = extract_text_from_url(url)
        else:
            return None, "Please provide either a PDF file or a URL."
        
        truncated_text = truncate_text(text)
        if len(truncated_text) < len(text):
            print("Warning: The input text was truncated to fit within 2048 tokens.")
        
        script = generate_script(SYSTEM_PROMPT, truncated_text, tone, length)
        
        audio_segments = []
        transcript = ""
        try:
            for item in script.dialogue:
                audio_file = generate_audio(item.text, item.speaker)
                audio_segment = AudioSegment.from_mp3(audio_file)
                audio_segments.append(audio_segment)
                transcript += f"**{item.speaker}**: {item.text}\n\n"
                os.remove(audio_file)  # Clean up temporary audio file
        except Exception as e:
            raise gr.Error(f"Error generating audio: {str(e)}")
        
        combined_audio = sum(audio_segments)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            combined_audio.export(temp_audio.name, format="mp3")
            temp_audio_path = temp_audio.name
        
        return temp_audio_path, transcript
    
    except Exception as e:
        return None, f"An error occurred: {str(e)}"

instructions = """
# Podify Studio
Welcome to the Podcast Generator ! This tool creates custom podcast episodes using AI-generated content.
"""

iface = gr.Interface(
    fn=generate_podcast,
    inputs=[
        gr.File(label="Upload PDF file (optional)", file_types=[".pdf"]),
        gr.Textbox(label="OR Enter URL"),
        gr.Radio(["humorous", "casual", "formal"], label="Select podcast tone", value="casual"),
        gr.Radio(["Short (1-2 min)", "Medium (3-5 min)"], label="Podcast length", value="Medium (3-5 min)")
    ],
    outputs=[
        gr.Audio(label="Generated Podcast"),
        gr.Markdown(label="Transcript")
    ],
    title="🎙️ Amuthvani:AI Podcast !",
    description=instructions,
    allow_flagging="never",
    theme=gr.themes.Soft()
)

if __name__ == "__main__":
    iface.launch()
