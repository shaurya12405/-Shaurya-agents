import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional, Set, Callable, List

logger = logging.getLogger(__name__)


class InterruptionDecision(str, Enum):
    IGNORE = "IGNORE"            # ignore while agent is speaking
    INTERRUPT = "INTERRUPT"      # stop TTS and hand control to user
    USER_SPEECH = "USER_SPEECH"  # normal user speech when agent is silent


@dataclass
class ASRResult:
    """Minimal ASR result abstraction to keep handler decoupled."""
    transcript: str
    confidence: Optional[float] = None
    duration_ms: Optional[int] = None
    timestamp_ms: Optional[int] = None


class InterruptionHandler:
    """Voice interruption logic built on top of LiveKit VAD+ASR."""

    def __init__(
        self,
        ignored_words: Iterable[str],
        interrupt_words: Iterable[str] = ("stop", "wait", "hold", "pause", "no", "dont", "don't"),
        min_confidence_for_filler: float = 0.7,
        min_segment_ms_for_noise: int = 150,
        stop_tts_callback: Optional[Callable[[], "asyncio.Future"]] = None,
    ):
        self._ignored_words: Set[str] = {w.strip().lower() for w in ignored_words if w.strip()}
        self._interrupt_words: Set[str] = {w.strip().lower() for w in interrupt_words if w.strip()}
        self._min_conf = float(min_confidence_for_filler)
        self._min_seg_ms = int(min_segment_ms_for_noise)
        self._agent_speaking: bool = False
        self._lock = asyncio.Lock()
        self._stop_tts = stop_tts_callback or (lambda: asyncio.get_event_loop().create_future())

    # ---------------- Agent speaking flags ---------------- #

    async def on_tts_start(self):
        async with self._lock:
            self._agent_speaking = True
        logger.debug("TTS started -> agent_speaking=True")

    async def on_tts_end(self):
        async with self._lock:
            self._agent_speaking = False
        logger.debug("TTS ended -> agent_speaking=False")

    # ---------------- Runtime update of filler words ---------------- #

    async def update_ignored_words(self, new_words: Iterable[str]):
        words = {w.strip().lower() for w in new_words if w.strip()}
        async with self._lock:
            self._ignored_words = words
        logger.info("Updated ignored_words to %s", sorted(self._ignored_words))

    # ---------------- Core ASR decision logic ---------------- #

    async def handle_asr(self, asr: ASRResult) -> InterruptionDecision:
        async with self._lock:
            agent_speaking = self._agent_speaking
            ignored = self._ignored_words.copy()
            interrupt_words = self._interrupt_words.copy()
            min_conf = self._min_conf
            min_seg_ms = self._min_seg_ms

        transcript = (asr.transcript or "").strip().lower()
        tokens: List[str] = [t for t in transcript.split() if t]

        has_tokens = len(tokens) > 0
        filler_only = has_tokens and all(t in ignored for t in tokens)
        command_present = any(t in interrupt_words for t in tokens)

        conf = asr.confidence
        low_conf = (conf is not None and conf < min_conf)
        seg_ms = asr.duration_ms or 0
        noise_short = seg_ms < min_seg_ms

        log_ctx = dict(
            transcript=transcript,
            confidence=conf,
            duration_ms=seg_ms,
            agent_speaking=agent_speaking,
            filler_only=filler_only,
            command_present=command_present,
        )

        if agent_speaking:

            if filler_only and not low_conf:
                logger.debug("IGNORE: filler-only during TTS | ctx=%s", log_ctx)
                return InterruptionDecision.IGNORE

            if command_present:
                await self._safe_stop_tts()
                logger.debug("INTERRUPT: command word | ctx=%s", log_ctx)
                return InterruptionDecision.INTERRUPT

            if has_tokens and not filler_only and not low_conf:
                await self._safe_stop_tts()
                logger.debug("INTERRUPT: non-filler during TTS | ctx=%s", log_ctx)
                return InterruptionDecision.INTERRUPT

            if low_conf or noise_short:
                logger.debug("IGNORE: low confidence/noise | ctx=%s", log_ctx)
                return InterruptionDecision.IGNORE

            logger.debug("IGNORE: default speaking branch | ctx=%s", log_ctx)
            return InterruptionDecision.IGNORE

        # Agent NOT speaking
        logger.debug("USER_SPEECH: agent silent | ctx=%s", log_ctx)
        return InterruptionDecision.USER_SPEECH

    async def _safe_stop_tts(self):
        try:
            maybe_future = self._stop_tts()
            if asyncio.isfuture(maybe_future) or asyncio.iscoroutine(maybe_future):
                await asyncio.shield(maybe_future)
        except Exception as e:
            logger.exception("stop_tts_callback raised: %s", e)
