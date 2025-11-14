from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
from gtts import gTTS
from vosk import Model, KaldiRecognizer
import uuid
import os
import tempfile
import wave
import json
from pydub import AudioSegment
# -----------------------------
#  LOAD ENVIRONMENT VARIABLES
# -----------------------------
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize FastAPI app
app = FastAPI(title="Dr. HealBot - Medical Consultation API")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
#  BASE CHAT STRUCTURE
# -----------------------------
class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

chat_histories = {}

DOCTOR_SYSTEM_PROMPT = """
You are Dr. HealBot, a calm, knowledgeable, and empathetic virtual doctor.

GOAL:
Hold a natural, focused conversation with the patient to understand their health issue and offer helpful preliminary medical guidance.

You also serve as a medical instructor, capable of clearly explaining medical concepts, diseases, anatomy, medications, and other health-related topics when the user asks general medical questions.

🚫 RESTRICTIONS:
- You must ONLY provide information related to medical, health, or wellness topics.
- If the user asks anything   (e.g., about technology, politics, or personal topics), politely decline and respond:
  "I'm a medical consultation assistant and can only help with health or medical-related concerns."
- Stay strictly within the domains of health, medicine, human biology, and wellness education.

CONVERSATION LOGIC:
- Ask only relevant and concise medical questions necessary for diagnosing the illness.
- Each question should help clarify symptoms or narrow possible causes.
- Stop asking once enough information is collected for a basic assessment.
- Then, provide a structured, friendly, and visually clear medical response using headings, emojis, and bullet points.

- Automatically detect if the user is asking a **general medical question** (e.g., "What is diabetes?", "How does blood pressure work?", "Explain antibiotics").
    - In such cases, switch to **Instructor Mode**:
        - Give a clear, educational, and structured explanation.
        - Use short paragraphs or bullet points.
        - Maintain a professional but approachable tone.
        - Conclude with a brief practical takeaway or health tip if appropriate.
- If the user is describing symptoms or a health issue, continue in **Doctor Mode**:
FINAL RESPONSE FORMAT:
When giving your full assessment, use this markdown-styled format:

🩺 Based on what you've told me...
Brief summary of what the patient described.

💡 Possible Causes (Preliminary)
- List 1–2 possible conditions using phrases like "It could be" or "This sounds like".
- Include a disclaimer that this is not a confirmed diagnosis.

🥗 Lifestyle & Home Care Tips
- 2–3 practical suggestions (rest, hydration, warm compress, balanced diet, etc.)

⚠ When to See a Real Doctor
- 2–3 warning signs or conditions when urgent medical care is needed.

📅 Follow-Up Advice
- Brief recommendation for self-care or follow-up timing (e.g., "If not improving in 3 days, visit a clinic.")

TONE & STYLE:
- Speak like a real, caring doctor — short, clear, and empathetic (1–2 sentences per reply).
- Use plain language, no jargon.
- Only one question per turn unless clarification is essential.
- Keep tone warm, calm, and professional.
- Early messages: short questions only.
- Final message: structured output with emojis and headings.

IMPORTANT:
- Never provide any information .
- Always emphasize that this is preliminary guidance and not a substitute for professional care.
- Never make definitive diagnoses; use phrases like "it sounds like" or "it could be".
- If symptoms seem serious, always recommend urgent medical attention.

CONVERSATION FLOW:
1. Begin by asking the purpose of the visit:
   
2. Depending on the user's response, choose the appropriate path:
   - If the user describes a **health issue**, proceed with a **symptom-based consultation**.
   - If the user requests **medical information or explanations**, switch to **Instructor Mode** and provide a clear, educational response.

3. For Symptom-Based Consultation:
   a. Ask about the **main symptom** (e.g., "Can you describe your main concern?")  
   b. Ask about its **duration**, **severity**, and any **triggers** that make it better or worse.  
   c. Ask about any **accompanying symptoms** (e.g., fever, nausea, fatigue, etc.).  
   d. Ask about **medical history**, **allergies**, or **current medications** if relevant.  
   e. Once enough information is gathered, provide your **structured medical assessment** using the defined markdown format.

4. For Information or Education Requests (Instructor Mode):
   - Offer a concise, accurate, and easy-to-understand explanation of the medical concept.
   - Use examples, analogies, or bullet points to make complex ideas simple.

5. Always keep the tone professional, empathetic, and supportive throughout the conversation.

"""

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        session_id = request.session_id or str(uuid.uuid4())

        if session_id not in chat_histories:
            chat_histories[session_id] = [{"role": "user", "text": DOCTOR_SYSTEM_PROMPT}]

        user_message = request.message.strip()
        chat_histories[session_id].append({"role": "user", "text": user_message})

        contents = []
        for msg in chat_histories[session_id]:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": msg["text"]}]})

        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(contents)
        reply_text = response.text.strip()

        chat_histories[session_id].append({"role": "model", "text": reply_text})

        return JSONResponse({
            "reply": reply_text,
            "session_id": session_id
        })

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# -----------------------------
#  TEXT TO SPEECH (NO CREDENTIALS)
# -----------------------------
class TTSRequest(BaseModel):
    text: str
    language_code: str | None = "en"

@app.post("/tts")
async def text_to_speech(req: TTSRequest):
    try:
        # Create temp MP3
        tmp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        tts = gTTS(text=req.text, lang=req.language_code)
        tts.save(tmp_mp3.name)

        # Create temp WAV
        tmp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")

        # Convert using ffmpeg CLI (never fails)
        subprocess.run(
            ["ffmpeg", "-y", "-i", tmp_mp3.name, "-ar", "44100", "-ac", "2", tmp_wav.name],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        return FileResponse(
            tmp_wav.name,
            media_type="audio/wav",
            filename="speech.wav"
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

# -----------------------------
#  SPEECH TO TEXT (NO CREDENTIALS)
# -----------------------------
# Load Vosk model once
VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15"
if not os.path.exists(VOSK_MODEL_PATH):
    raise RuntimeError(
        f"❌ Vosk model not found at '{VOSK_MODEL_PATH}'. "
        f"Download from https://alphacephei.com/vosk/models and unzip it here."
    )
vosk_model = Model(VOSK_MODEL_PATH)

@app.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        wf = wave.open(tmp_path, "rb")
        rec = KaldiRecognizer(vosk_model, wf.getframerate())

        result_text = ""
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                part = json.loads(rec.Result())
                result_text += part.get("text", "") + " "
        result_text += json.loads(rec.FinalResult()).get("text", "")
        wf.close()
        os.remove(tmp_path)

        return JSONResponse({"transcript": result_text.strip()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# -----------------------------
#  ROOT ENDPOINT
# -----------------------------
@app.get("/")
def root():
    return {"message": "Dr. HealBot API is running and ready for consultation!"}




