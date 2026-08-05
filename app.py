import os
import json
import glob
import time
import threading
import webbrowser
from flask import Flask, render_template, request, jsonify, send_from_directory
from generate_studio import run_pipeline, get_genai_client, suggest_collision_ideas, SCRIPT_FILE, PUBLISHED_FILE, EXTERNAL_YOUTUBE_DIR
from batch_studio import run_overnight_batch

app = Flask(__name__, template_folder="templates")
OUTPUT_DIR = os.path.abspath("output")
QUEUE_FILE = "weekly_queue.json"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/past_topics", methods=["GET"])
def get_past_topics_endpoint():
    try:
        from generate_studio import get_past_topics
        topics = get_past_topics()
        return jsonify({"status": "success", "count": len(topics), "topics": topics})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/ideas", methods=["GET"])
def get_ideas():
    try:
        refresh = request.args.get("refresh", "false").lower() == "true"
        client = get_genai_client()
        ideas = suggest_collision_ideas(client, force_refresh=refresh)
        return jsonify({"status": "success", "ideas": ideas})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/queue", methods=["GET", "POST"])
def manage_queue():
    if request.method == "POST":
        data = request.json or {}
        queue_items = data.get("queue", [])
        try:
            with open(QUEUE_FILE, "w", encoding="utf-8") as f:
                json.dump(queue_items, f, indent=2)
            return jsonify({"status": "success", "queue": queue_items})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    # GET method
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                queue_items = json.load(f)
                return jsonify({"queue": queue_items})
        except Exception as e:
            print(f"Error reading {QUEUE_FILE}: {e}")
    return jsonify({"queue": []})

@app.route("/api/projects", methods=["GET"])
def list_projects():
    projects = []
    
    # 1. Load published_videos.json items
    if os.path.exists(PUBLISHED_FILE):
        try:
            with open(PUBLISHED_FILE, "r", encoding="utf-8") as f:
                pub_data = json.load(f)
                for idx, p in enumerate(pub_data):
                    projects.append({
                        "folder_name": f"published_{idx+1}",
                        "timestamp": "Uploaded Video",
                        "concept_a": p.get("concept_a", ""),
                        "concept_b": p.get("concept_b", ""),
                        "script": f"Title: {p.get('title_hook')}\n\nTeaser: {p.get('teaser')}",
                        "scenes": [],
                        "has_audio": False,
                        "is_published": True
                    })
        except Exception as e:
            print(f"Error reading {PUBLISHED_FILE}: {e}")

    # 2. Match both local video_* and external YouTube channel project folders
    project_folders = sorted(
        glob.glob(os.path.join(OUTPUT_DIR, "video_*")) + glob.glob(os.path.join(OUTPUT_DIR, "project_*")), 
        reverse=True
    )
    if os.path.exists(EXTERNAL_YOUTUBE_DIR):
        ext_folders = sorted(glob.glob(os.path.join(EXTERNAL_YOUTUBE_DIR, "*")), reverse=True)
        project_folders.extend(ext_folders)
    
    seen_folders = set()
    for folder in project_folders:
        meta_path = os.path.join(folder, "metadata.json")
        folder_name = os.path.basename(folder)
        if folder_name in seen_folders:
            continue
        
        if os.path.exists(meta_path):
            seen_folders.add(folder_name)
            with open(meta_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    data["folder_name"] = folder_name
                    images = sorted([os.path.basename(p) for p in glob.glob(os.path.join(folder, "scene_*.png"))])
                    has_audio = os.path.exists(os.path.join(folder, "voiceover.wav"))
                    data["image_files"] = images
                    data["has_audio"] = has_audio
                    projects.append(data)
                except Exception as e:
                    print(f"Error reading {meta_path}: {e}")
                    
    return jsonify({"projects": projects})

@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.json or {}
    concept_a = data.get("concept_a")
    concept_b = data.get("concept_b")
    custom_script = data.get("custom_script")
    voice = data.get("voice", "F4")
    speed = float(data.get("speed", 0.90))
    target_duration = float(data.get("target_duration", 1.5))
    scene_mode = data.get("scene_mode", "hold_and_polish")

    try:
        project_data = run_pipeline(
            concept_a=concept_a,
            concept_b=concept_b,
            custom_script=custom_script,
            voice=voice,
            speed=speed,
            target_duration=target_duration,
            scene_mode=scene_mode
        )
        if project_data:
            return jsonify({"status": "success", "project": project_data})
        else:
            return jsonify({"status": "error", "message": "Failed to generate assets"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/batch", methods=["POST"])
def trigger_batch():
    data = request.json or {}
    selected_ideas = data.get("selected_ideas", [])
    voice = data.get("voice", "F4")
    speed = float(data.get("speed", 0.90))
    scene_mode = data.get("scene_mode", "hold_and_polish")

    # If no selected_ideas sent in request, try reading weekly_queue.json
    if not selected_ideas and os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                selected_ideas = json.load(f)
        except Exception:
            pass

    if not selected_ideas or len(selected_ideas) == 0:
        return jsonify({"status": "error", "message": "No approved ideas in queue. Please select ideas first!"}), 400

    def start_batch_thread():
        run_overnight_batch(selected_ideas=selected_ideas, voice=voice, speed=speed, scene_mode=scene_mode)

    threading.Thread(target=start_batch_thread).start()
    return jsonify({"status": "success", "message": f"Overnight batch process started for {len(selected_ideas)} approved videos ({scene_mode} mode)."})

@app.route("/api/web-generate-images", methods=["POST"])
def trigger_web_images():
    data = request.json or {}
    max_videos = int(data.get("max_videos", 2))

    try:
        from web_automation import run_web_image_automation, find_incomplete_projects
        missing = find_incomplete_projects()
        if not missing:
            return jsonify({"status": "info", "message": "All projects in /output already have 100% complete scene images!"})

        def start_web_automation_thread():
            run_web_image_automation(max_videos=max_videos)

        threading.Thread(target=start_web_automation_thread).start()
        return jsonify({
            "status": "success",
            "message": f"Playwright Chrome automation started! Processing {min(len(missing), max_videos)} complete video packages.",
            "incomplete_videos_count": len(missing)
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/shutdown", methods=["POST"])
def shutdown():
    def delayed_exit():
        time.sleep(1)
        print("  👋 Shutting down Studio Dashboard server...")
        os._exit(0)

    threading.Thread(target=delayed_exit).start()
    return jsonify({"status": "success", "message": "Studio server process terminating."})

@app.route("/output/<folder>/<filename>")
def serve_output_file(folder, filename):
    target_folder = os.path.join(OUTPUT_DIR, folder)
    return send_from_directory(target_folder, filename)

@app.route("/female.png")
def serve_female_ref():
    return send_from_directory(os.path.abspath("."), "female.png")

@app.route("/male.png")
def serve_male_ref():
    return send_from_directory(os.path.abspath("."), "male.png")

@app.route("/character_ref.png")
def serve_char_ref():
    return send_from_directory(os.path.abspath("."), "female.png")

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    print("=" * 60)
    print("  🚀 MR. NOBODY STUDIO DASHBOARD ONLINE")
    print("  👉 Dashboard URL: http://127.0.0.1:5000")
    print("=" * 60)
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
