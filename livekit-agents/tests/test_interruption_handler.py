import pytest
import pytest_asyncio

from livekit.agents.extensions.interruption_handler import (
    InterruptionHandler,
    ASRResult,
    InterruptionDecision,
)

@pytest_asyncio.fixture
async def handler():
    h = InterruptionHandler(
        ignored_words=["uh", "umm", "hmm"],
        interrupt_words=["stop", "wait"],
        min_confidence_for_filler=0.7,
        min_segment_ms_for_noise=150,
    )
    return h

@pytest.mark.asyncio
async def test_filler_ignored_when_speaking(handler):
    await handler.on_tts_start()
    result = await handler.handle_asr(ASRResult("uh", 0.8, 200))
    assert result == InterruptionDecision.IGNORE

@pytest.mark.asyncio
async def test_interrupt_command(handler):
    await handler.on_tts_start()
    result = await handler.handle_asr(ASRResult("stop", 0.9, 300))
    assert result == InterruptionDecision.INTERRUPT

@pytest.mark.asyncio
async def test_non_filler_interrupts(handler):
    await handler.on_tts_start()
    result = await handler.handle_asr(ASRResult("hello", 0.9, 200))
    assert result == InterruptionDecision.INTERRUPT

@pytest.mark.asyncio
async def test_low_confidence_noise_ignored(handler):
    await handler.on_tts_start()
    result = await handler.handle_asr(ASRResult("noise", 0.1, 100))
    assert result == InterruptionDecision.IGNORE

@pytest.mark.asyncio
async def test_filler_accepted_when_quiet(handler):
    await handler.on_tts_end()
    result = await handler.handle_asr(ASRResult("umm", 0.9, 200))
    assert result == InterruptionDecision.USER_SPEECH

@pytest.mark.asyncio
async def test_dynamic_update(handler):
    await handler.update_ignored_words(["hmmmmm"])
    await handler.on_tts_start()
    result = await handler.handle_asr(ASRResult("hmmmmm", 0.9, 200))
    assert result == InterruptionDecision.IGNORE
