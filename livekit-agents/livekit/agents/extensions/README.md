## Voice Interruption Handler – Feature Branch

This branch adds a new feature to the LiveKit Agents repo:
a small system that helps the agent understand when the user is trying to interrupt while the agent is speaking.

## 1. What Changed

In this branch, I added a new folder:

`livekit-agents/livekit/agents/extensions/`

Inside it, I added two files:

- `interruption_handler.py` → *main logic*
- `__init__.py` → *contains files for import*

I also added a test file:

`livekit-agents/tests/test_interruption_handler.py`

The interruption handler decides three things:

- **IGNORE** → ignore filler words like "uh", "umm", etc.
- **INTERRUPT** → stop TTS when user says words like "stop", "wait", etc.
- **USER_SPEECH** → normal speech when the agent is silent


## 2. What Works

These features were tested and work properly:

- Filler words are ignored when the agent is speaking  
- Interrupt words correctly stop the agent  
- Low-confidence noise is ignored  
- Filler words count as normal speech when the agent is not speaking  
- Ignored words can be updated during runtime  
- All tests pass using pytest


## 3. Known Issues

- Not yet connected to a real-time LiveKit audio session  
- Interrupt and filler word lists are simple and may need improvement  
- No real microphone / live audio testing  
- Currently supports basic English filler words


## 4. Steps to Test

### **A. Automated Tests**

Run:
`pytest -q`
This checks:

- filler ignored  
- interrupt word detected  
- noise ignored  
- normal speech handling  
- updating ignored words

---

## 5. Environment Details

- Python 3.9+  
- Libraries needed:  
  - `pytest`  
  - `pytest-asyncio`  
- Works on Windows, macOS, Linux

Install test packages:
`pip install pytest pytest-asyncio`

