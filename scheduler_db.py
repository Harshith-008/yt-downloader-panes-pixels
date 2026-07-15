import os
import json
import uuid
from datetime import datetime

SCHEDULER_FILE = os.path.join(os.path.expanduser("~"), ".yt_shorts_downloader_scheduler.json")

def load_schedule():
    if os.path.exists(SCHEDULER_FILE):
        try:
            with open(SCHEDULER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_schedule(tasks):
    try:
        with open(SCHEDULER_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, indent=2)
    except Exception as e:
        print(f"Error saving schedule: {e}")

def add_task(video_path, platform, caption, scheduled_time_str, uniquifier_opts):
    """
    video_path: Absolute path to video file
    platform: 'youtube' or 'instagram'
    caption: text description for post
    scheduled_time_str: datetime string format 'YYYY-MM-DD HH:MM'
    uniquifier_opts: dict containing: {'mirror': bool, 'speed': bool, 'contrast': bool, 'scrub': bool}
    """
    tasks = load_schedule()
    
    # Generate a unique task ID
    task_id = f"task_{uuid.uuid4().hex[:8]}"
    
    new_task = {
        "id": task_id,
        "video_path": video_path,
        "platform": platform,
        "caption": caption,
        "scheduled_time": scheduled_time_str,
        "status": "scheduled",
        "error_msg": None,
        "uniquifier_opts": uniquifier_opts,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    tasks.append(new_task)
    save_schedule(tasks)
    return new_task

def update_task_status(task_id, status, error_msg=None):
    tasks = load_schedule()
    for task in tasks:
        if task["id"] == task_id:
            task["status"] = status
            task["error_msg"] = error_msg
            break
    save_schedule(tasks)

def delete_task(task_id):
    tasks = load_schedule()
    filtered_tasks = [t for t in tasks if t["id"] != task_id]
    save_schedule(filtered_tasks)
