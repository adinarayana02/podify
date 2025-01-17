from groq import Groq
from pydantic import BaseModel, ValidationError
from typing import List, Literal
import os
import tiktoken
import json
import re
import tempfile
from gtts import gTTS
from bs4 import BeautifulSoup
import requests

groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
tokenizer = tiktoken.get_encoding("cl100k_base")

class DialogueItem(BaseModel):
    speaker: Literal["Priya", "Ananya"]
    text: str

class Dialogue(BaseModel):
    dialogue: List[DialogueItem]

def truncate_text(text, max_tokens=2048):
    tokens = tokenizer.encode(text)
    if len(tokens) > max_tokens:
        return tokenizer.decode(tokens[:max_tokens])
    return text

def extract_text_from_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        raise ValueError(f"Error extracting text from URL: {str(e)}")

def generate_script(system_prompt: str, input_text: str, tone: str, target_length: str):
    input_text = truncate_text(input_text)
    word_limit = 300 if target_length == "Short (1-2 min)" else 750
    
    prompt = f"""
    {system_prompt}
    TONE: {tone}
    TARGET LENGTH: {target_length} (approximately {word_limit} words)
    INPUT TEXT: {input_text}
    Generate a complete, well-structured podcast script that:
    1. Starts with a friendly, engaging introduction that feels natural, welcoming the listeners as if Priya and Ananya are speaking directly to them.
    2. Covers the main points from the input text in a conversational, relaxed manner with smooth transitions. Priya (American accent) and Ananya (British accent) should engage in a back-and-forth conversation that feels authentic and lively, as if two people are having a real interaction.
    3. Voice adjustments: Ensure that the flow of conversation is natural, with slight pauses for thought and clear enunciation, making it easy for all listeners to follow along. Keep the pace relaxed but steady, with slight variations in speed for emphasis on key points—ensuring clarity and ease of understanding.
    4. Concludes with a smooth and heartfelt summary, wrapping up the discussion in a way that feels genuine and leaves listeners with a sense of closure, while thanking them for tuning in.
    5. The overall voice speed and tone should match the conversation and topic, ensuring the dialogue is easy to comprehend. For more intense moments, you can use a slightly faster pace for energy, and for reflective points, use a slower, thoughtful pace.
    6. Fits within the {word_limit} word limit for the target length of {target_length}.
    7. Strongly emphasizes the {tone} tone throughout the conversation. 
    For a humorous tone, include jokes, puns, and playful banter, making the conversation feel light-hearted while integrating subtle cultural references and humor that listeners can relate to.
    For a casual tone, use colloquial language and friendly expressions that make it feel like a relaxed, informal chat between friends. Include cultural references and inside jokes to keep the conversation fun.
    For a formal tone, maintain a professional style with clear, structured arguments, presenting information with respect and authority, but still keeping the conversation friendly and accessible.
    Ensure the script feels like a real, flowing podcast conversation without abrupt transitions or unnatural interruptions.
"""

    
    response = groq_client.chat.completions.create(
        messages=[
            {"role": "system", "content": prompt},
        ],
        model="llama-3.1-70b-versatile",
        max_tokens=2048,
        temperature=0.7
    )
    
    content = response.choices[0].message.content
    content = re.sub(r'```json\s*|\s*```', '', content)
    
    try:
        json_data = json.loads(content)
        dialogue = Dialogue.model_validate(json_data)
    except json.JSONDecodeError as json_error:
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            try:
                json_data = json.loads(match.group())
                dialogue = Dialogue.model_validate(json_data)
            except (json.JSONDecodeError, ValidationError) as e:
                raise ValueError(f"Failed to parse dialogue JSON: {e}\nContent: {content}")
        else:
            raise ValueError(f"Failed to find valid JSON in the response: {content}")
    except ValidationError as e:
        raise ValueError(f"Failed to validate dialogue structure: {e}\nContent: {content}")
    
    return dialogue

def generate_audio(text: str, speaker: str) -> str:
    tld = 'com' if speaker == "Priya" else 'co.in'
    tts = gTTS(text=text, lang='en', tld=tld)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        tts.save(temp_audio.name)
        return temp_audio.name
