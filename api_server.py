import os
import pandas as pd
import base64
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import edge_tts
from groq import Groq
from chatbot_engine import get_chatbot_chain
from dotenv import load_dotenv

load_dotenv()

from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Mount the admin_panel directory to serve static HTML files
app.mount("/admin_panel", StaticFiles(directory="admin_panel"), name="admin_panel")

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

# Groq Client Initialization
groq_client = None

def get_groq_client():
    global groq_client
    if groq_client is None:
        groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return groq_client

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

from fastapi.responses import FileResponse

@app.get("/api/leads")
async def get_leads():
    if not os.path.exists(LEADS_FILE):
        return []
    try:
        df = pd.read_csv(LEADS_FILE)
        # Replace NaN with empty string for JSON compatibility
        df = df.fillna("")
        return df.to_dict(orient="records")
    except Exception as e:
        print(f"Error reading leads: {e}")
        return []

@app.get("/api/download-csv")
async def download_csv():
    if not os.path.exists(LEADS_FILE):
        raise HTTPException(status_code=404, detail="Lead data file not found")
    return FileResponse(LEADS_FILE, media_type="text/csv", filename="svsu_leads.csv")
async def voice_chat(audio_file: UploadFile = File(...)):
    client = get_groq_client()
    if not client:
        raise HTTPException(status_code=503, detail="Groq API not configured")
    
    try:
        # 1. Save uploaded file to temp_audio
        file_id = str(uuid.uuid4())
        input_path = f"temp_audio/{file_id}.wav"
        
        with open(input_path, "wb") as f:
            f.write(await audio_file.read())

        # 2. Transcribe STT using Groq Whisper API (Lightning Fast)
        print(f"Transcribing audio with Groq API: {input_path}")
        with open(input_path, "rb") as fileData:
            transcription = client.audio.transcriptions.create(
                file=(input_path, fileData.read()),
                model="whisper-large-v3",
                response_format="json",
                language="en",
                temperature=0.0
            )

        user_text = transcription.text.strip()
        
        if not user_text:
            return {"transcription": "", "response": "Sorry, I couldn't hear anything clearly.", "audio": ""}

        # 3. Get LLM Response
        bot_response = qa_chain({"question": user_text})

        # 4. Convert to Speech (TTS) using edge-tts (Lightning Fast & Ultra Natural)
        output_path = f"temp_audio/{file_id}.mp3"
        communicate = edge_tts.Communicate(bot_response, "en-US-AriaNeural")
        await communicate.save(output_path)

        # 5. Read output and encode as base64
        with open(output_path, "rb") as f:
            audio_base64 = base64.b64encode(f.read()).decode('utf-8')

        # Cleanup temp files
        if os.path.exists(input_path): os.remove(input_path)
        if os.path.exists(output_path): os.remove(output_path)

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
