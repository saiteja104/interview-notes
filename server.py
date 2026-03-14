from fastapi import FastAPI, Request
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mock_api")

app = FastAPI()

# A dictionary to remember who is currently talking in each interview
active_speakers = {}

@app.post("/internal/interviews/{interview_id}/status")
async def update_status(interview_id: str, request: Request):
    data = await request.json()
    log.info(f"[{interview_id}] STATUS UPDATE: {data}")
    return {"status": "ok"}

# 1. CATCH THE REAL NAME FROM THE ZOOM UI
@app.post("/internal/interviews/{interview_id}/speaker")
async def receive_speaker(interview_id: str, request: Request):
    data = await request.json()
    speaker_name = data.get("name", "Unknown")
    
    # Update the current active speaker for this meeting
    active_speakers[interview_id] = speaker_name
    log.info(f"[{interview_id}] UI DETECTED SPEAKER: {speaker_name}")
    return {"status": "ok"}

# 2. ATTACH THE NAME TO THE AZURE TRANSCRIPT
@app.post("/internal/interviews/{interview_id}/transcript")
async def receive_transcript(interview_id: str, request: Request):
    data = await request.json()
    text = data.get('text', '')
    is_final = data.get('is_final', False)
    
    # Look up who the UI says is currently talking
    current_name = active_speakers.get(interview_id, "Unknown Speaker")

    # Only print and save if it is the FINAL polished sentence
    if is_final and text.strip():
        log_line = f"Speaker [{current_name}]: {text}"
        log.info(f"[{interview_id}] TRANSCRIPT: {log_line}")
        
        # Save to file
        filename = f"{interview_id}_transcript.txt"
        with open(filename, "a", encoding="utf-8") as f:
            f.write(f"{log_line}\n")
            
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)