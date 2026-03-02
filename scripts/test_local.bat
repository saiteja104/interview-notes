@echo off
set MEETING_URL=https://us04web.zoom.us/j/73850955863?pwd=BZaZ6ZtrUMEVqRpubNF87tSGKIRBR2.1
set INTERVIEW_ID=test-001
set BOT_NAME=Interview Assistant
set API_BASE_URL=http://host.docker.internal:8000
set DEEPGRAM_API_KEY=4b46ec0127fca32c0097a2ac3d1263c88b7d6dc7

docker rm -f zoom-bot-test 2>nul

docker run ^
    --name zoom-bot-test ^
    -e MEETING_URL="%MEETING_URL%" ^
    -e INTERVIEW_ID="%INTERVIEW_ID%" ^
    -e BOT_NAME="%BOT_NAME%" ^
    -e API_BASE_URL="%API_BASE_URL%" ^
    -e DEEPGRAM_API_KEY="%DEEPGRAM_API_KEY%" ^
    --cap-add=SYS_ADMIN ^
    --security-opt seccomp=unconfined ^
    --memory="2g" ^
    --cpus="1.0" ^
    zoom-bot:local