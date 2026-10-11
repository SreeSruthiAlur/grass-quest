import yaml
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

DEFAULT_CONFIG = """
models:
  text: "llama3.2:latest"
  vision: "moondream"
ollama:
  base_url: "http://localhost:11434"
app:
  db_path: "data/grass_quest.db"
  max_retries: 3
  temperature: 0.1
"""

def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w") as f:
            f.write(DEFAULT_CONFIG.strip())
    
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)

config = load_config()
