import os
import pandas as pd
import base64
import uuid
import whisper
from datetime import datetime
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from gtts import gTTS
from chatbot_engine import get_chatbot_chain
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Create temp directories for audio processing
if not os.path.exists("data"): os.makedirs("data")
if not os.path.exists("temp_audio"): os.makedirs("temp_audio")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model cache
voice_model = None

def get_voice_model():
    global voice_model
    if voice_model is None:
        print("Loading Whisper model (base) - this may take a moment...")
        voice_model = whisper.load_model("base")
    return voice_model

qa_chain = get_chatbot_chain()

LEADS_FILE = "data/leads.csv"

class LeadData(BaseModel):
    name: str
    email: str
    mobile: str
    designation: str
    purpose: str

class ChatRequest(BaseModel):
    question: str

@app.get("/")
async def root():
    return {"status": "SVSU Intelligent API with Voice is running"}

@app.post("/api/lead")
async def save_lead(data: LeadData):
    try:
        lead_dict = data.dict()
        lead_dict['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_exists = os.path.isfile(LEADS_FILE)
        df = pd.DataFrame([lead_dict])
        df.to_csv(LEADS_FILE, mode='a', index=False, header=not file_exists)
        return {"status": "success", "message": "Lead saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        response = qa_chain({"question": request.question})
        return {"response": response}
    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice-chat")
async def voice_chat(audio_file: UploadFile = File(...)):
    model = get_voice_model()
    if not model:
        raise HTTPException(status_code=503, detail="Voice model not loaded")
    
    try:
        # 1. Save uploaded file to temp_audio
        file_id = str(uuid.uuid4())
        input_path = f"temp_audio/{file_id}.wav"
        
        with open(input_path, "wb") as f:
            f.write(await audio_file.read())

        # 2. Transcribe STT
        print(f"Transcribing audio: {input_path}")
        result = model.transcribe(input_path)
        user_text = result["text"].strip()
        
        if not user_text:
            return {"transcription": "", "response": "Sorry, I couldn't hear anything clearly.", "audio": ""}

        # 3. Get LLM Response
        bot_response = qa_chain({"question": user_text})

        # 4. Convert to Speech (TTS)
        # Using gTTS for speed and reliability in MVP
        output_path = f"temp_audio/{file_id}.mp3"
        tts = gTTS(text=bot_response, lang='en')
        tts.save(output_path)

        # 5. Read output and encode as base64
        with open(output_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')

        # Cleanup temp files (optional but good practice)
        os.remove(input_path)
        os.remove(output_path)

        return {
            "transcription": user_text,
            "response": bot_response,
            "audio": audio_base64
        }
    except Exception as e:
        print(f"Voice Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
