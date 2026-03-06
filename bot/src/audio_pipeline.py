import asyncio
import json
import logging
import subprocess

import websockets

log = logging.getLogger("audio_pipeline")

DEEPGRAM_URL = (
    "wss://api.deepgram.com/v1/listen"
    "?model=nova-2"
    "&language=en"
    "&punctuate=true"
    "&diarize=true"
    "&interim_results=true"
    "&endpointing=300"
    "&smart_format=true"
    "&keepalive=true"
)


class AudioPipeline:
    def __init__(self, deepgram_api_key: str, interview_id: str, api):
        self.deepgram_api_key = deepgram_api_key
        self.interview_id     = interview_id
        self.api              = api
        self._ffmpeg_proc     = None

    async def run(self, stop_event: asyncio.Event):
        log.info("Starting audio pipeline...")
        await asyncio.sleep(3)

        try:
            async with websockets.connect(
                DEEPGRAM_URL,
                extra_headers={"Authorization": f"Token {self.deepgram_api_key}"},
                ping_interval=20,
                ping_timeout=10,
            ) as ws:
                log.info("Connected to Deepgram")
                self._ffmpeg_proc = self._start_ffmpeg()
                log.info("FFmpeg capturing audio")

                await asyncio.gather(
                    self._send_audio(ws, stop_event),
                    self._receive_transcripts(ws),
                    self._keepalive(ws, stop_event),
                    self._watch_stop(ws, stop_event),
                )
        except Exception as e:
            log.error(f"Audio pipeline error: {e}", exc_info=True)
        finally:
            self._kill_ffmpeg()

    def _start_ffmpeg(self):
        return subprocess.Popen(
            [
                "ffmpeg",
                "-f", "pulse",
                "-i", "virtual_speaker.monitor",
                "-ar", "16000",
                "-ac", "1",
                "-f", "s16le",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    async def _send_audio(self, ws, stop_event: asyncio.Event):
        loop = asyncio.get_event_loop()
        while not stop_event.is_set():
            chunk = await loop.run_in_executor(
                None, self._ffmpeg_proc.stdout.read, 4096
            )
            if not chunk:
                break
            try:
                await ws.send(chunk)
            except websockets.ConnectionClosed:
                break

        try:
            await ws.send(json.dumps({"type": "CloseStream"}))
        except Exception:
            pass

    # async def _receive_transcripts(self, ws):
    #     async for raw in ws:
    #         try:
    #             msg = json.loads(raw)
    #             if msg.get("type") != "Results":
    #                 continue

    #             alt        = msg["channel"]["alternatives"][0]
    #             transcript = alt.get("transcript", "").strip()
    #             is_final   = msg.get("is_final", False)
    #             words      = alt.get("words", [])

    #             if not transcript:
    #                 continue

    #             speaker_id = words[0].get("speaker") if words else None
    #             log.info(f"[{'FINAL' if is_final else 'interim'}] Speaker {speaker_id}: {transcript}")

    #             await self.api.send_transcript(
    #                 text=transcript,
    #                 speaker_id=speaker_id,
    #                 words=words,
    #                 is_final=is_final,
    #             )
    #         except Exception as e:
    #             log.error(f"Transcript error: {e}")


    async def _receive_transcripts(self, ws):
        async for raw in ws:
            try:
                msg = json.loads(raw)
                
                # Catch and print ANY Deepgram errors immediately
                if msg.get("type") == "Error" or "error" in msg:
                    log.error(f"DEEPGRAM ERROR: {msg}")
                    continue

                if msg.get("type") != "Results":
                    continue

                alt        = msg["channel"]["alternatives"][0]
                transcript = alt.get("transcript", "").strip()
                is_final   = msg.get("is_final", False)
                words      = alt.get("words", [])

                if not transcript:
                    continue

                speaker_id = words[0].get("speaker") if words else None
                log.info(f"[{'FINAL' if is_final else 'interim'}] Speaker {speaker_id}: {transcript}")

                await self.api.send_transcript(
                    text=transcript,
                    speaker_id=speaker_id,
                    words=words,
                    is_final=is_final,
                )
            except Exception as e:
                log.error(f"Transcript error: {e}")

    async def _keepalive(self, ws, stop_event: asyncio.Event):
        while not stop_event.is_set():
            await asyncio.sleep(8)
            try:
                await ws.send(json.dumps({"type": "KeepAlive"}))
            except Exception:
                break

    async def _watch_stop(self, ws, stop_event: asyncio.Event):
        await stop_event.wait()
        try:
            await ws.close()
        except Exception:
            pass

    def _kill_ffmpeg(self):
        if self._ffmpeg_proc:
            self._ffmpeg_proc.terminate()
            self._ffmpeg_proc.wait()

    async def stop(self):
        self._kill_ffmpeg()