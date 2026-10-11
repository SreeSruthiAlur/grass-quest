# Grass Quest 🌿

A local-first web app that gets you off screens and into nature. Powered by local AI via Ollama.

## Why Open Models?
Grass Quest is built on the belief that your connection with nature shouldn't come at the cost of your digital privacy. By using open-weight models running locally (Ollama), we ensure:
- **Zero Cloud APIs:** Your data never leaves your machine.
- **Offline First:** No internet? No problem.
- **Sustainability:** Run on your own hardware.

## Setup

1. **Install Ollama:** Download and install from [ollama.com](https://ollama.com).
2. **Pull Models:**
   ```powershell
   ollama pull llama3.2:latest
   ollama pull moondream
   ```
3. **Install Dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
4. **Run the App:**
   ```powershell
   ./start.ps1
   ```
5. **Open Browser:** Navigate to `http://localhost:8000`.

## Model Swap Guide
You can change the models used in `app/config.yaml`. Simply update the `text` or `vision` model names and restart the app. Ensure the models are pulled via Ollama first.

## License
MIT
