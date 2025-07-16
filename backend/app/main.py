from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import ChatRequest, FeedbackRequest
from . import services
from dotenv import load_dotenv
import ollama

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # 1. Extraire les paramètres de recherche (requête, unité et valeur de temps)
        search_params = services.extract_search_parameters(request.message)
        query = search_params.get("requete", request.message)
        time_unit = search_params.get("unite_temps", "any")
        time_value = search_params.get("valeur_temps", 0)

        # 2. Chercher sur le web avec les paramètres mis à jour
        search_results = services.search_web(query, time_unit, time_value)
        
        if not search_results:
            raise HTTPException(status_code=404, detail="Impossible de trouver des informations pertinentes pour la période spécifiée.")
        
        # 3. Synthétiser la réponse (inchangé)
        final_answer = services.synthesize_answer(request.message, search_results)
        
        return {"answer": final_answer}

    except Exception as e:
        print(f"Une erreur est survenue dans chat_endpoint: {e}")
        raise HTTPException(status_code=500, detail="Une erreur interne du serveur est survenue.")

# The root and feedback endpoints remain the same
@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/api/feedback")
async def feedback_endpoint(request: FeedbackRequest):
    try:
        services.save_feedback(request)
        return {"status": "success", "message": "Feedback bien reçu. Merci !"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))