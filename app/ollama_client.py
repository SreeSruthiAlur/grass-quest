import httpx
import json
import logging
from pydantic import BaseModel, ValidationError
from typing import Type, TypeVar, Optional, List
from .config import config

T = TypeVar("T", bound=BaseModel)

logger = logging.getLogger(__name__)

class OllamaClient:
    def __init__(self):
        self.base_url = config["ollama"]["base_url"]
        self.text_model = config["models"]["text"]
        self.vision_model = config["models"]["vision"]
        self.max_retries = config["app"]["max_retries"]
        self.temperature = config["app"]["temperature"]

    async def generate_json(self, prompt: str, schema: Type[T]) -> T:
        """Generates JSON from the text model and validates it against a schema with retries."""
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/api/generate",
                        json={
                            "model": self.text_model,
                            "prompt": prompt,
                            "format": "json",
                            "stream": False,
                            "options": {
                                "temperature": self.temperature
                            }
                        }
                    )
                    response.raise_for_status()
                    data = response.json()
                    content = data.get("response", "")
                    
                    # Parse and validate
                    parsed_json = json.loads(content)
                    return schema.model_validate(parsed_json)
            except (httpx.HTTPError, json.JSONDecodeError, ValidationError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt == self.max_retries - 1:
                    raise Exception(f"Failed to generate valid JSON after {self.max_retries} attempts. Last error: {e}")
        
        raise Exception("Unreachable code")

    async def generate_text(self, prompt: str) -> str:
        """Generates a text response from the text model."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.text_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7
                        }
                    }
                )
                response.raise_for_status()
                return response.json().get("response", "")
        except httpx.HTTPError as e:
            raise Exception(f"Ollama text generation failed: {e}. Is Ollama running? Try: ollama serve")

    async def describe_image(self, image_bytes: bytes) -> str:
        """Generates a description of an image using the vision model."""
        import base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.vision_model,
                        "prompt": "Describe this photo briefly focus on nature, plants, textures, and objects.",
                        "images": [image_b64],
                        "stream": False
                    }
                )
                response.raise_for_status()
                return response.json().get("response", "")
        except httpx.HTTPError as e:
            raise Exception(f"Ollama vision generation failed: {e}. Is Ollama running? Try: ollama serve")

ollama_client = OllamaClient()
