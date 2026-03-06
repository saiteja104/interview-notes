import logging
from fastapi import FastAPI, Request
import uvicorn

# Set up logging so you can see the bot's messages in your terminal
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mock_api")

app = FastAPI()

# Endpoint to catch status updates (e.g., "joining", "waiting_room", "active")
@app.post("/internal/interviews/{interview_id}/status")
async def update_status(interview_id: str, request: Request):
    data = await request.json()
    log.info(f"[{interview_id}] STATUS UPDATE: {data}")
    return {"status": "ok"}

# Endpoint to catch the live audio transcripts from Deepgram
# @app.post("/internal/interviews/{interview_id}/transcript")
# async def receive_transcript(interview_id: str, request: Request):
#     data = await request.json()
#     log.info(f"[{interview_id}] TRANSCRIPT: Speaker {data.get('speaker_id')}: {data.get('text')}")
#     return {"status": "ok"}


import os # Add this at the top of your file if it isn't there

@app.post("/internal/interviews/{interview_id}/transcript")
async def receive_transcript(interview_id: str, request: Request):
    data = await request.json()
    speaker = data.get('speaker_id', 'Unknown')
    text = data.get('text', '')
    
    # 1. Print it to the terminal (so you can still watch it live)
    log.info(f"[{interview_id}] TRANSCRIPT: Speaker {speaker}: {text}")
    
    # 2. Save it permanently to a text file in the same folder
    filename = f"{interview_id}_transcript.txt"
    with open(filename, "a", encoding="utf-8") as f:
        f.write(f"Speaker {speaker}: {text}\n")
        
    return {"status": "ok"}

# Endpoint to catch who is currently speaking (video highlights)
@app.post("/internal/interviews/{interview_id}/speaker")
async def speaker_event(interview_id: str, request: Request):
    data = await request.json()
    log.info(f"[{interview_id}] SPEAKER: {data.get('name')}")
    return {"status": "ok"}

if __name__ == "__main__":
    # This runs the server on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)