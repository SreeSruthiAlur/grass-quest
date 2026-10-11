from typing import List
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import os
import uuid
import logging

from .database import init_db, get_db, Quest
from .ollama_client import ollama_client
from .schemas import QuestCreate, QuestSchema, PhotoMatchResult, JournalResponse, TaskSchema
from .config import config

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Grass Quest")

# Create uploads directory
UPLOAD_DIR = "app/static/assets/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Mount static files and templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
async def read_root(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.post("/api/quests", response_model=QuestSchema)
async def create_quest(quest_in: QuestCreate, db: Session = Depends(get_db)):
    month = datetime.now().strftime("%B")
    time_of_day = datetime.now().strftime("%I:%M %p")
    
    prompt = f"""
    Generate a 'quest card' for a nature walk.
    Environment: {quest_in.environment}
    Difficulty: {quest_in.difficulty}
    Duration: {quest_in.duration} minutes
    Current Month: {month}
    Time of Day: {time_of_day}

    The quest must have exactly 6 tasks: 
    1. observe (visual)
    2. listen (auditory)
    3. touch-safe textures (tactile)
    4. count (numerical)
    5. find-by-shape
    6. find-by-color

    Tasks must be doable with the phone in a pocket. No scanning tasks.
    Output MUST be strict JSON matching this schema:
    {{
      "tasks": [
        {{"id": 1, "text": "task description", "type": "type"}},
        ...
      ]
    }}
    """
    
    try:
        quest_data = await ollama_client.generate_json(prompt, QuestSchema)
        
        # Save to DB
        tasks_db = []
        for t in quest_data.tasks:
            tasks_db.append({
                "id": t.id,
                "text": t.text,
                "type": t.type,
                "status": "pending",
                "photo_description": None,
                "confidence": "none"
            })
            
        db_quest = Quest(
            environment=quest_in.environment,
            difficulty=quest_in.difficulty,
            duration=quest_in.duration,
            tasks=tasks_db
        )
        db.add(db_quest)
        db.commit()
        db.refresh(db_quest)
        
        return quest_data
    except Exception as e:
        logger.error(f"Error creating quest: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/quests/latest")
async def get_latest_quest(db: Session = Depends(get_db)):
    quest = db.query(Quest).order_by(Quest.created_at.desc()).first()
    if not quest:
        raise HTTPException(status_code=404, detail="No quests found")
    return quest

@app.post("/api/quests/{quest_id}/match-photos")
async def match_photos(quest_id: int, files: List[UploadFile] = File(...), db: Session = Depends(get_db)):
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    results = []
    tasks = quest.tasks
    
    for file in files:
        contents = await file.read()
        # Save photo
        file_ext = os.path.splitext(file.filename)[1]
        file_name = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, file_name)
        with open(file_path, "wb") as f:
            f.write(contents)
            
        # Get description from vision model
        description = await ollama_client.describe_image(contents)
        
        # Match description to tasks
        task_list_str = "\n".join([f"{t['id']}: {t['text']}" for t in tasks])
        match_prompt = f"""
        A user took a photo during a nature walk. 
        Description of the photo: {description}
        
        Available tasks:
        {task_list_str}
        
        Which task does this photo likely satisfy? 
        If it matches a task, label it 'likely'. If it's a stretch, label it 'unsure'. If it matches nothing, label it 'none'.
        
        Output MUST be strict JSON:
        {{
            "task_id": 1,
            "confidence": "likely",
            "explanation": "why it matches"
        }}
        """
        
        try:
            match_result = await ollama_client.generate_json(match_prompt, PhotoMatchResult)
            if match_result.confidence != "none":
                # Update task status
                for t in tasks:
                    if t['id'] == match_result.task_id:
                        t['status'] = 'completed'
                        t['photo_description'] = description
                        t['confidence'] = match_result.confidence
                        results.append(match_result)
        except Exception as e:
            logger.error(f"Error matching photo: {e}")
            
    quest.tasks = tasks
    quest.is_completed = True
    db.commit()
    
    return results

@app.post("/api/quests/{quest_id}/journal", response_model=JournalResponse)
async def generate_journal(quest_id: int, db: Session = Depends(get_db)):
    quest = db.query(Quest).filter(Quest.id == quest_id).first()
    if not quest:
        raise HTTPException(status_code=404, detail="Quest not found")
    
    completed_tasks = [t['text'] for t in quest.tasks if t['status'] == 'completed']
    if not completed_tasks:
        journal_text = "I went for a walk today. It was peaceful, even if I didn't complete any specific tasks."
    else:
        tasks_str = ", ".join(completed_tasks)
        prompt = f"Write a short, warm 100-word nature journal entry about a walk in a {quest.environment} where I did these things: {tasks_str}. Keep it reflective and appreciative of the outdoors."
        journal_text = await ollama_client.generate_text(prompt)
        
    quest.journal_entry = journal_text
    db.commit()
    
    return JournalResponse(journal=journal_text)

@app.get("/api/history")
async def get_history(db: Session = Depends(get_db)):
    quests = db.query(Quest).order_by(Quest.created_at.desc()).all()
    
    # Calculate streak (days outside this week)
    today = datetime.utcnow().date()
    start_of_week = today - timedelta(days=today.weekday())
    
    days_this_week = db.query(Quest).filter(Quest.created_at >= start_of_week).all()
    unique_days = set([q.created_at.date() for q in days_this_week])
    streak = len(unique_days)
    
    return {
        "history": quests,
        "streak": streak
    }
