# 🎬 YouTube Automation Studio — AI Narrative Pipeline

An automated, open-source content generation engine for producing minimalist, high-retention observational YouTube videos and storytelling assets using Google Gemini, prompt post-processing heuristics, and local speech synthesis.

---

## 🏗️ System Architecture & Workflow

```text
[ Collision System ] ──► Pair mundane Concept A (everyday habit) with Concept B (psychological trait)
         │
         ▼
[ Script Generator ] ──► Generates 5-part observational script via Gemini 2.0/3.5 Flash
         │
         ▼
[ Storyboard Director ] ──► Parses script into 10–18 dense micro-scenes with static framing
         │
         ▼
[ Prompt Post-Processor ] ──► Sanitizes motion verbs, removes sci-fi overlays, attaches character anchors
         │
         ├─► Exports /output/video_xxx/prompts_guide.txt (Ready for Imagen 3 / Playwright)
         └─► Synthesizes /output/video_xxx/voiceover.wav via local Supertonic TTS (0.90x)
```

---

## 🛠️ Deep Technical Specifications

### 1. Collision & Script Generation Engine (`generate_studio.py`)
- **System Instruction Constraints (`SYSTEM_SCRIPT_INSTRUCTION`)**: Enforces a strict 5-part narrative arc (Hook $\to$ Collision & Delayed Reveal $\to$ Escalation $\to$ Hidden Principle $\to$ Unresolved Irony Ending).
- **TTS Pacing Rules**: Forces one thought per line, restricts sentence lengths (8–15 words), bans academic/explanatory jargon (*"We feel compelled to..."*), and mandatorily strips exclamation marks.
- **Model Fallback Sequence**: Automatically fails over across `gemini-flash-latest`, `gemini-2.0-flash-lite`, and `gemini-3.5-flash` with exponential backoff handling for `RESOURCE_EXHAUSTED (429)` quota resets.

### 2. Micro-Scene Parser & Prompt Sanitization Engine
- **Dense Segmentation (`parse_script_to_scenes`)**: Guarantees a minimum scene density threshold (`MIN_REQUIRED_SCENES = 10`), re-parsing any incomplete scenes automatically.
- **Regex Motion Sanitizer (`sanitize_visual_prompt`)**: Strips dynamic camera movement instructions (`montage`, `camera pull-away`, `tracking shot`, `push-in`, `tilts up`) and converts them into static final-frame compositions.
- **Grounded Realism Filter**: Eliminates CGI/sci-fi forcefields, glowing geometric overlays, and futuristic visual tropes, replacing them with physical distance and real-world lighting.
- **Contextual Character Anchor Injection (`build_full_prompt`)**: Detects whether the scene features the recurring character or observer. Dynamically attaches `Use the attached female character reference...` when the observer is present, or defaults to clean `Cinematic editorial storybook illustration` for pure environment/object close-ups to prevent prompt contradictions.

### 3. Audio & Voiceover Synthesis Pipeline
- **Supertonic HTTP Integration**: Sends payload requests to local Supertonic TTS server (`http://127.0.0.1:7788/v1/audio/speech`).
- **Pacing Settings**: Configured for voice `F4` at `0.90x` playback speed, outputting 16-bit uncompressed WAV audio (`voiceover.wav`).

### 4. Studio Dashboard & Overnight Batch Processing
- **Flask REST Server (`app.py`)**: Local management dashboard serving JSON APIs for collision idea caching (`ideas_cache.json`), weekly queue management (`weekly_queue.json`), and project metadata serving (`metadata.json`).
- **Async Batch Studio (`batch_studio.py`)**: Multithreaded overnight worker executing batch queues sequentially with configurable pauses (`IMAGE_GENERATION_PAUSE = 10s`, `VIDEO_BATCH_PAUSE = 60s`).

---

## 🎥 The 7 Golden Rules of Observer Cinematography

All prompt generation pipeline rules are derived from the locked channel framework:

1. **Observer Perspective Framing**: Frame secondary subjects through the recurring observer's presence (*"Over-the-shoulder shot from behind the recurring female observer watching..."*).
2. **Static Frame Rule**: Describe the still composition of the final frame; strictly ban dynamic camera motion verbs.
3. **Grounded Realism**: Translate abstract psychological metaphors into subtle real-world physical arrangements.
4. **No Film Equipment Jargon**: Describe the picture itself, not camera hardware.
5. **Emotional Mood Sentence**: Every prompt includes one sentence detailing the subject's psychological state.
6. **Quality & Restraint Shield**: Appends global negative prompt rules (*"Avoid horror aesthetics, exaggerated expressions, surreal distortions, text, logos..."*).
7. **Visual Rhythm**: Progress dynamically across shot types (`Close-up` $\to$ `Extreme Close-up` $\to$ `Wide` $\to$ `Environmental Detail` $\to$ `Over-the-shoulder`).

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone git@github.com:rohitpadile/Youtube_Automation_Using_AI_101.git
cd Youtube_Automation
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` in the root directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
SUPERTONIC_URL=http://127.0.0.1:7788/v1/audio/speech
```

### 3. Run Pipeline via CLI

```bash
# Generate video assets for a collision pair
python generate_studio.py --concept-a "Earphones with No Audio" --concept-b "Social Armor"

# Brainstorm 20 fresh collision ideas
python generate_studio.py --ideas
```

### 4. Launch Studio Dashboard

```bash
python app.py
```
Navigate to `http://127.0.0.1:5000` to manage queues and trigger batch generation.

---

## 📁 Package Structure

```text
output/video_20260727_223715_earphones_with_no_audio_x_social_armor/
├── script.txt          # Synthesized narrative script
├── prompts_guide.txt   # Copy-paste prompts guide for Playwright / Imagen 3
├── metadata.json       # Project scene metadata & parameters
└── voiceover.wav       # 0.90x Supertonic voiceover WAV file
```

---

## 🛡️ Security & Licensing

Private branding assets (`female.png`, `male.png`, `channel_config.json`, `MR_NOBODY_FRAMEWORK.md`) and generated output folders are protected under `.gitignore`.
