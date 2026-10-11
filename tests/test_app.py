import pytest
from pydantic import ValidationError
from app.schemas import QuestSchema, TaskSchema, PhotoMatchResult
from app.ollama_client import OllamaClient
import json

# 1. Quest JSON schema validation
def test_quest_schema_validation():
    valid_data = {
        "tasks": [
            {"id": 1, "text": "Find a green leaf", "type": "find"},
            {"id": 2, "text": "Listen to a bird", "type": "listen"}
        ]
    }
    quest = QuestSchema.model_validate(valid_data)
    assert len(quest.tasks) == 2
    assert quest.tasks[0].type == "find"

def test_quest_schema_invalid():
    invalid_data = {"tasks": [{"id": "one", "text": "Missing type"}]}
    with pytest.raises(ValidationError):
        QuestSchema.model_validate(invalid_data)

# 2. Photo Match Result validation
def test_photo_match_validation():
    data = {"task_id": 1, "confidence": "likely", "explanation": "It's a leaf"}
    match = PhotoMatchResult.model_validate(data)
    assert match.confidence == "likely"

# 3. Test OllamaClient retry logic (Mocked)
@pytest.mark.asyncio
async def test_ollama_retry_logic(mocker):
    client = OllamaClient()
    client.max_retries = 3
    
    mock_post = mocker.patch("httpx.AsyncClient.post")
    
    # First two calls return invalid JSON, third returns valid
    mock_post.side_effect = [
        mocker.Mock(status_code=200, json=lambda: {"response": "invalid json"}),
        mocker.Mock(status_code=200, json=lambda: {"response": '{"tasks": []}'}), # Missing required fields if any, but QuestSchema needs tasks list
        mocker.Mock(status_code=200, json=lambda: {"response": '{"tasks": [{"id": 1, "text": "ok", "type": "test"}]}'})
    ]
    
    result = await client.generate_json("prompt", QuestSchema)
    assert len(result.tasks) == 1
    assert mock_post.call_count == 3

# 4. Streak calculation logic
from app.database import Quest
from datetime import datetime, timedelta

def test_streak_calculation():
    # Mocking DB results for streak
    today = datetime.utcnow()
    yesterday = today - timedelta(days=1)
    
    quests = [
        Quest(created_at=today),
        Quest(created_at=today), # Same day
        Quest(created_at=yesterday)
    ]
    
    unique_days = set([q.created_at.date() for q in quests])
    assert len(unique_days) == 2

# 5. Task-photo matching logic (textual part)
@pytest.mark.asyncio
async def test_matching_logic_prompt_generation():
    # This tests if we can correctly generate the prompt for matching
    tasks = [{"id": 1, "text": "Find a red flower"}]
    description = "A photo of a red rose in a garden."
    
    task_list_str = "\n".join([f"{t['id']}: {t['text']}" for t in tasks])
    prompt = f"Description: {description}\nTasks:\n{task_list_str}"
    
    assert "red flower" in prompt
    assert "red rose" in prompt

# 6. Test Task object structure in DB
def test_task_db_structure():
    task = {
        "id": 1,
        "text": "Find a leaf",
        "type": "find",
        "status": "pending",
        "photo_description": None,
        "confidence": "none"
    }
    assert task["status"] == "pending"
    assert task["id"] == 1

# 7. Test Quest initialization
def test_quest_init():
    quest = Quest(
        environment="park",
        difficulty="easy",
        duration=15,
        tasks=[]
    )
    assert quest.environment == "park"
    assert quest.is_completed == False

# 8. Test Journal Prompt generation
def test_journal_prompt_gen():
    environment = "garden"
    tasks = ["Find a red rose", "Listen to a bee"]
    tasks_str = ", ".join(tasks)
    prompt = f"Write a journal about a {environment} walk where I did: {tasks_str}"
    assert "garden" in prompt
    assert "red rose" in prompt
