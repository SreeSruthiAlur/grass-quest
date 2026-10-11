from pydantic import BaseModel
from typing import List, Optional

class TaskSchema(BaseModel):
    id: int
    text: str
    type: str # observe, listen, touch, count, find

class QuestSchema(BaseModel):
    tasks: List[TaskSchema]

class QuestCreate(BaseModel):
    duration: int
    difficulty: str
    environment: str

class PhotoMatchResult(BaseModel):
    task_id: int
    confidence: str # likely, unsure, none
    explanation: str

class JournalResponse(BaseModel):
    journal: str
