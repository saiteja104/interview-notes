@echo off
set "MEETING_URL=https://app.zoom.us/wc/81790228998/start?fromPWA=1&pwd=cERPGgix4BLOqPwodeICZnIX58tXjq.1"
set "INTERVIEW_ID=test-001"
set "BOT_NAME=Interview Assistant"
set "API_BASE_URL=http://172.27.160.1:8000"



docker rm -f zoom-bot-test 2>nul

docker run ^
    --name zoom-bot-test ^
    -e MEETING_URL="%MEETING_URL%" ^
    -e INTERVIEW_ID="%INTERVIEW_ID%" ^
    -e BOT_NAME="%BOT_NAME%" ^
    -e API_BASE_URL="%API_BASE_URL%" ^
    -e AZURE_SPEECH_KEY="%AZURE_SPEECH_KEY%" ^
    -e AZURE_SPEECH_REGION="%AZURE_SPEECH_REGION%" ^
    -v "%cd%\screenshots:/app/screenshots" ^
    --cap-add=SYS_ADMIN ^
    --security-opt seccomp=unconfined ^
    --memory="2g" ^
    --cpus="1.0" ^
    zoom-bot:local