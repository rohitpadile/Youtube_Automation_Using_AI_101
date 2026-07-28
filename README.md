# 🎬 YouTube Automation Studio — AI Narrative Pipeline

An automated content generation engine for producing minimalist, high-retention observational YouTube videos and storytelling assets using Google Gemini and local speech synthesis.

---

## 🌟 Key Features

- **The Collision Engine**: Automatically pairs everyday mundane objects with subtle psychological tendencies to write high-hook, observant scripts.
- **Dense Micro-Scene Storyboarding**: Parses scripts sentence-by-sentence into structured 16:9 visual prompts designed for static image models (Imagen 3, Midjourney, Flux).
- **Prompt Guide Exporter**: Generates clean, copy-paste-ready `prompts_guide.txt` files formatted with negative prompt rules, character consistency anchors, and emotional composition guides.
- **Local Voiceover Synthesis**: Integrates with local Supertonic TTS for natural, custom-paced voiceover generation (`.wav`).
- **Studio Dashboard & Overnight Batch**: Local Flask web application (`app.py`) and batch queue execution (`batch_studio.py`) for automated weekly production.

---

## 🚀 Quick Start

### 1. Prerequisites & Installation

Ensure Python 3.10+ is installed on your system.

```bash
git clone <your-repo-url>
cd Youtube_Automation
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the root directory:

```env
GEMINI_API_KEY=your_gemini_api_key_here
SUPERTONIC_URL=http://127.0.0.1:7788/v1/audio/speech
```

### 3. Generate Video Assets via CLI

Run the asset generator with your chosen collision concepts:

```bash
# Generate video script, prompts guide, and voiceover
python generate_studio.py --concept-a "Earphones with No Audio" --concept-b "Social Armor"

# Brainstorm 20 fresh collision ideas
python generate_studio.py --ideas
```

### 4. Launch Web Studio Dashboard

```bash
python app.py
```
Open `http://127.0.0.1:5000` in your browser to approve ideas, manage weekly queues, and generate video packages visually.

---

## 📁 Output Directory Structure

Each generated video is packaged into a self-contained project folder inside `/output`:

```text
output/video_20260727_223715_earphones_with_no_audio_x_social_armor/
├── script.txt          # Voiceover narrative text
├── prompts_guide.txt   # Structured visual image prompts guide
├── metadata.json       # Structured project & scene metadata
└── voiceover.wav       # Synthesized TTS voiceover audio
```

---

## 🛡️ License & Privacy

Private custom branding assets (`female.png`, `male.png`, `channel_config.json`, `MR_NOBODY_FRAMEWORK.md`) and generated media output files are protected under `.gitignore` and excluded from repository tracking.
