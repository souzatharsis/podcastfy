import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Dict, Union, List, cast

from pydub import AudioSegment as PydubAudioSegment

from podcastfy.core.podcast import SyncTTSBackend, AsyncTTSBackend
from podcastfy.core.transcript import TranscriptSegment, Transcript


class AudioSegment:
    """Represents an audio segment of the podcast."""

    def __init__(self, filepath: Path, length_ms: int, transcript_segment: Optional[TranscriptSegment] = None) -> None:
        self.filepath = filepath
        self.length_ms = length_ms
        self.transcript_segment = transcript_segment
        self._audio: Optional[PydubAudioSegment] = None

    @property
    def audio(self) -> PydubAudioSegment:
        """Lazy-load the audio segment."""
        if self._audio is None:
            self._audio = PydubAudioSegment.from_file(self.filepath)
            if len(self._audio) != self.length_ms:
                raise ValueError(
                    f"Audio file length ({len(self._audio)}ms) does not match specified length ({self.length_ms}ms)")
        return self._audio


class AudioManager:
    def __init__(self, tts_backends: Dict[str, Union[SyncTTSBackend, AsyncTTSBackend]], n_jobs: int = 1) -> None:
        self.tts_backends = tts_backends
        self.n_jobs = n_jobs
        self.audio_segments = []
        self.final_audio: Optional[PydubAudioSegment] = None
        self.temp_dir: Optional[Union[str, Path]] = None

    async def _async_build_audio_segments(self, transcript: Transcript) -> List[AudioSegment]:
        async def process_segment(segment: TranscriptSegment):
            tts_backend = self.get_tts_backend(segment)
            audio_file = await cast(AsyncTTSBackend, tts_backend).async_text_to_speech(
                segment.text,
                segment.speaker,
                Path(self.temp_dir) / f"{segment.speaker.name}_{len(self.audio_segments)}.mp3"
            )
            return AudioSegment(audio_file, len(PydubAudioSegment.from_file(str(audio_file))), segment)

        semaphore = asyncio.Semaphore(self.n_jobs)

        async def bounded_process_segment(segment):
            async with semaphore:
                return await process_segment(segment)

        tasks = [asyncio.create_task(bounded_process_segment(segment)) for segment in transcript.segments]
        return list(await asyncio.gather(*tasks))

    def get_tts_backend(self, segment):
        if segment.speaker.preferred_tts is None:
            # take the first available TTS backend
            tts_backend = next(iter(self.tts_backends.values()))
        else:
            tts_backend = self.tts_backends[segment.speaker.preferred_tts]
            # ensure the preferred TTS backend is available
            if tts_backend is None:
                raise ValueError(f"Preferred TTS backend '{segment.speaker.preferred_tts}' is not available for character '{segment.speaker.name}'")
        return tts_backend

    def _sync_build_audio_segments(self, transcript: Transcript) -> List[AudioSegment]:
        def process_segment(segment: TranscriptSegment):
            tts_backend = self.get_tts_backend(segment)
            audio_file = cast(SyncTTSBackend, tts_backend).text_to_speech(
                segment.text,
                segment.speaker,
                Path(str(self.temp_dir)) / f"{segment.speaker.name}_{len(self.audio_segments)}.mp3"
            )
            return AudioSegment(audio_file, len(PydubAudioSegment.from_file(str(audio_file))), segment)


        with ThreadPoolExecutor(max_workers=self.n_jobs) as executor:
            return list(executor.map(process_segment, transcript.segments))

    def create_audio_segments(self, transcript: Transcript) -> List[AudioSegment]:
        if all(isinstance(backend, AsyncTTSBackend) for backend in self.tts_backends.values()):
            return asyncio.run(self._async_build_audio_segments(transcript))
        else:
            return self._sync_build_audio_segments(transcript)

    def stitch_audio_segments(self) -> None:
        self.final_audio = sum([segment.audio for segment in self.audio_segments])
