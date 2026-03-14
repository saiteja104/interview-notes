import asyncio
import logging
import subprocess
import os
import azure.cognitiveservices.speech as speechsdk

log = logging.getLogger("audio_pipeline")

class AudioPipeline:
    def __init__(self, unused_key: str, interview_id: str, api):
        # We ignore the old Deepgram key passed by bot.py and grab Azure directly
        self.azure_key = os.getenv("AZURE_SPEECH_KEY")
        self.azure_region = os.getenv("AZURE_SPEECH_REGION")
        self.interview_id = interview_id
        self.api = api
        
        self._ffmpeg_proc = None
        self._push_stream = None
        self._recognizer = None

    async def run(self, stop_event: asyncio.Event):
        log.info("Starting Azure audio pipeline...")
        await asyncio.sleep(3)

        loop = asyncio.get_event_loop()

        # 1. Configure Azure Speech (Creating a Client Basically.)
        speech_config = speechsdk.SpeechConfig(subscription=self.azure_key, region=self.azure_region)
        speech_config.speech_recognition_language = "en-US"
        
        # 2. Configure the Audio Push Stream (16kHz, 16-bit, Mono)
        stream_format = speechsdk.audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1)
        self._push_stream = speechsdk.audio.PushAudioInputStream(stream_format=stream_format)
        audio_config = speechsdk.audio.AudioConfig(stream=self._push_stream)

        # 3. Initialize Recognizer
        self._recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)

        # 4. Define Azure Background Callbacks
        def recognizing_cb(evt):
            text = evt.result.text
            if text:
                log.info(f"[interim] Azure: {text}")
                # Safely send back to the main async event loop
                # asyncio.run_coroutine_threadsafe(
                #     self.api.send_transcript(text=text, speaker_id="0", words=[], is_final=False),
                #     loop
                # )

        def recognized_cb(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                text = evt.result.text
                if text:
                    log.info(f"[FINAL] Azure: {text}")
                    asyncio.run_coroutine_threadsafe(
                        self.api.send_transcript(text=text, speaker_name="0", words=[], is_final=True),
                        loop
                    )

        # 5. Connect events and start listening
        self._recognizer.recognizing.connect(recognizing_cb)
        self._recognizer.recognized.connect(recognized_cb)
        self._recognizer.start_continuous_recognition()
        log.info("Azure connected and actively listening")

        # 6. Start FFmpeg
        self._ffmpeg_proc = self._start_ffmpeg()
        log.info("FFmpeg capturing audio")

        try:
            # Run the audio pushing loop alongside a stop watcher
            await asyncio.gather(
                self._push_audio(stop_event),
                self._watch_stop(stop_event)
            )
        except Exception as e:
            log.error(f"Audio pipeline error: {e}")
        finally:
            self._recognizer.stop_continuous_recognition()
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

    async def _push_audio(self, stop_event: asyncio.Event):
        loop = asyncio.get_event_loop()
        while not stop_event.is_set():
            # Read a chunk of bytes from FFmpeg
            chunk = await loop.run_in_executor(None, self._ffmpeg_proc.stdout.read, 4096)
            if not chunk:
                break
            
            # Push the raw bytes directly into Azure's brain
            if self._push_stream:
                self._push_stream.write(chunk)

    async def _watch_stop(self, stop_event: asyncio.Event):
        await stop_event.wait()
        if self._push_stream:
            self._push_stream.close()

    def _kill_ffmpeg(self):
        if self._ffmpeg_proc:
            self._ffmpeg_proc.terminate()
            self._ffmpeg_proc.wait()

    async def stop(self):
        self._kill_ffmpeg()