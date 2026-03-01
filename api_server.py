from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import pandas as pd
from datetime import datetime
from chatbot_engine import get_chatbot_chain
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Chatbot Chain
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
    return {"status": "SVSU Intelligent API is running"}

@app.post("/api/lead")
async def save_lead(data: LeadData):
    try:
        lead_dict = data.dict()
        lead_dict['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if not os.path.exists("data"):
            os.makedirs("data")
            
        file_exists = os.path.isfile(LEADS_FILE)
        df = pd.DataFrame([lead_dict])
        df.to_csv(LEADS_FILE, mode='a', index=False, header=not file_exists)
        
        return {"status": "success", "message": "Lead saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        # Call the chatbot engine
        if callable(qa_chain) and not hasattr(qa_chain, 'invoke'):
            full_response = qa_chain({"question": request.question})
        else:
            full_response = qa_chain.invoke(request.question)
            
        return {"response": full_response}
    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
