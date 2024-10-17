import asyncio
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Dict, Union, List, cast, Tuple

from pydub import AudioSegment

from podcastfy.core.podcast import SyncTTSBackend, AsyncTTSBackend
from podcastfy.core.transcript import TranscriptSegment, Transcript


class PodcastsAudioSegment:
    """Represents an audio segment of the podcast."""

    def __init__(self, filepath: Path, transcript_segment: Optional[TranscriptSegment] = None) -> None:
        self.filepath = filepath
        self.transcript_segment = transcript_segment
        self._audio: Optional[AudioSegment] = None

    @property
    def audio(self) -> AudioSegment:
        """Lazy-load the audio segment."""
        if self._audio is None:
            self._audio = AudioSegment.from_file(self.filepath)
        return self._audio


class AudioManager:
    def __init__(self, tts_backends: Dict[str, Union[SyncTTSBackend, AsyncTTSBackend]], n_jobs: int = 4, file_prefix: str = "") -> None:
        self.tts_backends = tts_backends
        self.n_jobs = n_jobs
        self.has_async_backend = any(isinstance(backend, AsyncTTSBackend) for backend in self.tts_backends.values())
        self.file_prefix = file_prefix
        self.audio_segments = []
        self.final_audio: Optional[AudioSegment] = None
        self.temp_dir: Optional[Union[str, Path]] = None

    async def _async_build_audio_segments(self, transcript: Transcript) -> List[PodcastsAudioSegment]:
        async def process_segment(segment_tuple: Tuple[TranscriptSegment, int]):
            segment, index = segment_tuple
            tts_backend = self.get_tts_backend(segment)
            audio_path = Path(self.temp_dir) / f"{self.file_prefix}{index:04d}.mp3"
            if isinstance(tts_backend, AsyncTTSBackend):
                await tts_backend.async_text_to_speech(
                    segment.text,
                    segment.speaker,
                    audio_path
                )
            else:
                tts_backend.text_to_speech(
                    segment.text,
                    segment.speaker,
                    audio_path
                )
            return PodcastsAudioSegment(audio_path, segment)

        semaphore = asyncio.Semaphore(self.n_jobs)

        async def bounded_process_segment(segment_tuple):
            async with semaphore:
                return await process_segment(segment_tuple)

        tasks = [asyncio.create_task(bounded_process_segment((segment, i))) for i, segment in enumerate(transcript.segments)]
        return list(await asyncio.gather(*tasks))

    def get_tts_backend(self, segment):
        tts_backend = self.tts_backends.get(segment.speaker.preferred_tts)
        if tts_backend is None:
            # Take the first available TTS backend
            tts_backend = next(iter(self.tts_backends.values()))
        return tts_backend

    def _sync_build_audio_segments(self, transcript: Transcript) -> List[PodcastsAudioSegment]:
        def process_segment(segment_tuple: Tuple[TranscriptSegment, int]):
            segment, index = segment_tuple
            tts_backend = self.get_tts_backend(segment)
            filepath = Path(str(self.temp_dir)) / f"{self.file_prefix}{index:04d}.mp3"
            cast(SyncTTSBackend, tts_backend).text_to_speech(
                segment.text,
                segment.speaker,
                filepath
            )
            return PodcastsAudioSegment(filepath, segment)


        with ThreadPoolExecutor(max_workers=self.n_jobs) as executor:
            return list(executor.map(process_segment,
                                     ((segment, i) for i, segment in enumerate(transcript.segments))))

    def create_audio_segments(self, transcript: Transcript) -> List[PodcastsAudioSegment]:
        if self.has_async_backend:
            return asyncio.run(self._async_build_audio_segments(transcript))
        else:
            return self._sync_build_audio_segments(transcript)

    # def stitch_audio_segments(self) -> None:
    #     self.final_audio = sum((segment.audio for segment in self.audio_segments), AudioSegment.empty())
