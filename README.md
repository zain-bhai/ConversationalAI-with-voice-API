# ConversationalAI-with-Voice-API  

### ⚠️ Important Notes
1. The **/chat** endpoint returns **Markdown text**. You must convert it into **HTML/markup** on your frontend.  
2. The **chat request** requires two fields:
   - `message`
   - `session_id`  
   The frontend must manage the `session_id`. Conversation history for each session is stored internally.  
3. The API includes **three endpoints**:
   - **/chat** → Conversational AI (returns markdown text)  
   - **/tts** → Text-to-Speech (returns `.wav` file)  
   - **/stt** → Speech-to-Text (returns transcription + `.wav` file)  

---

## 🚀 Getting Started

Follow these steps to run the API locally.

---

## 📋 Prerequisites

Make sure the following are installed:

- Python **3.9+**
- **pip** (Python package manager)
- **git** (for cloning the repository)

---

## 📥 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/zain-bhai/ConversationalAI-with-voice-API.git
cd ConversationalAI-with-voice-API


NOTE: install git first if you dont have installed yet.

3. Create a Virtual Environment (Recommended)
   
python -m venv venv

source venv/bin/activate       # On Windows: venv\Scripts\activate

4. Install Dependencies
pip install -r requirements.txt

5. Run the Application
python -m uvicorn app:app --reload --host 0.0.0.0 --port 8000


The API will start locally at:
👉 http://127.0.0.1:8000

Interactive API docs are available at:
👉 http://127.0.0.1:8000/docs  

Deployment (General Instructions)

This API can run on any system that supports Python.
To deploy it:

Copy all project files to your server or environment.

Install dependencies with pip install -r requirements.txt.

Start the FastAPI app:

uvicorn app:app --host 0.0.0.0 --port 8000

Ensure port 8000 (or your chosen port) is open for access.

No additional setup, keys, or dependencies are required.

Testing the API

Once running, test endpoints via:

Browser Swagger UI: http://127.0.0.1:8000/docs

Curl/Postman: Send requests manually for validation.

