@echo off
set "MEETING_URL=https://us05web.zoom.us/j/84447900892?pwd=kINQtwGNKwOs9GE9QqmCvRONqRPI0Y.1"
set "INTERVIEW_ID=test-001"
set "BOT_NAME=Interview Assistant"
set "API_BASE_URL=http://172.27.160.1:8000"
set "DEEPGRAM_API_KEY=4b46ec0127fca32c0097a2ac3d1263c88b7d6dc7"

docker rm -f zoom-bot-test 2>nul

docker run ^
    --name zoom-bot-test ^
    -e MEETING_URL="%MEETING_URL%" ^
    -e INTERVIEW_ID="%INTERVIEW_ID%" ^
    -e BOT_NAME="%BOT_NAME%" ^
    -e API_BASE_URL="%API_BASE_URL%" ^
    -e DEEPGRAM_API_KEY="%DEEPGRAM_API_KEY%" ^
    -v "%cd%\screenshots:/app/screenshots" ^
    --cap-add=SYS_ADMIN ^
    --security-opt seccomp=unconfined ^
    --memory="2g" ^
    --cpus="1.0" ^
    zoom-bot:local