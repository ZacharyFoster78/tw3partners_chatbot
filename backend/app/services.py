import ollama
import requests
import os
import json
import hashlib
from datetime import datetime
from serpapi import GoogleSearch


def print_log_decorator(func):
    def wrapper(*args, **kwargs):
        print(f"Appel de la fonction : {func.__name__}")
        result = func(*args, **kwargs)
        print(f"Résultat de {func.__name__} : {result}")
        return result
    return wrapper

# pour respecter la limite les requêtes à SerpAPI
import threading

SERPAPI_COUNTER_FILE = "serpapi_counter.json"
SERPAPI_DAILY_LIMIT = 100
SERPAPI_LOCK = threading.Lock()

def can_make_serpapi_request():
    from datetime import date
    import json

    today = date.today().isoformat()
    with SERPAPI_LOCK:
        if os.path.exists(SERPAPI_COUNTER_FILE):
            with open(SERPAPI_COUNTER_FILE, "r") as f:
                data = json.load(f)
        else:
            data = {}

        count = data.get(today, 0)
        if count >= SERPAPI_DAILY_LIMIT:
            return False

        data[today] = count + 1
        with open(SERPAPI_COUNTER_FILE, "w") as f:
            json.dump(data, f)
        return True

@print_log_decorator
def extract_search_parameters(question: str) -> dict:
    """
    Utilise le LLM pour extraire une requête de recherche et des filtres de temps (unité et valeur).
    Retourne un objet JSON.
    """
    system_prompt = """
    Tu es un expert dans l'analyse de requêtes utilisateur pour un moteur de recherche web.
    Ta tâche est d'extraire une requête de recherche concise et des paramètres de temps optionnels. Tes requêtes ne doivent pas contenir de sites web. 
    Les unités de temps possibles sont : "jour", "semaine", "mois", "an", ou "any".
    La date actuelle est """ + datetime.now().strftime('%Y-%m-%d') + """.

    - Si aucune durée spécifique n'est mentionnée, utilise "any" pour l'unité et 0 pour la valeur.
    - Si une durée est mentionnée (ex: "les 3 derniers jours", "cette semaine", "le mois dernier"), extrais la valeur numérique et l'unité de temps correspondante. "Cette semaine" ou "la semaine dernière" équivaut à 1 semaine.

    Réponds avec un objet JSON contenant trois clés : "requete", "unite_temps", et "valeur_temps" et ne dit rien d'autres.
    Exemples :
    Utilisateur: "Quelles sont les annonces de Google sur les ordinateurs quantiques des 3 derniers jours ?"
    {"requete": "annonces Google IA générative", "unite_temps": "jour", "valeur_temps": 3}
    
    Utilisateur: "Les nouveautés de la semaine sur React."
    {"requete": "nouveautés React", "unite_temps": "semaine", "valeur_temps": 1}

    Utilisateur: "Histoire de France"
    {"requete": "Histoire de France", "unite_temps": "any", "valeur_temps": 0}
    """
    try:
        response = ollama.chat(
            model='qwen2.5',
            format='json',
            messages=[
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': question},
            ]
        )
        params = json.loads(response['message']['content'])
        return params
    except Exception as e:
        print(f"Erreur lors de l'extraction des paramètres de recherche : {e}")
        return {"requete": question, "unite_temps": "any", "valeur_temps": 0}


@print_log_decorator
def search_web(query: str, time_unit: str = "any", time_value: int = 0):
    """
    Effectue une recherche web en utilisant SerpAPI.
    """
    print(f"Recherche de '{query}' avec le filtre temporel : {time_value} {time_unit}(s).")
    if not can_make_serpapi_request():
        print("Limite quotidienne SerpAPI atteinte.")
        return []
    try:
        api_key = os.getenv("SERPAPI_KEY")
        params = {
            "engine": "google",
            "q": query,
            "api_key": api_key,
            "num": 10,
        }

        # Mapping des unités de temps en français vers les codes SerpAPI/Google
        time_unit_map = {"jour": "d", "semaine": "w", "mois": "m", "an": "y"}
        if time_unit in time_unit_map and time_value > 0:
            params['tbs'] = f"qdr:{time_unit_map[time_unit]}{time_value if time_value > 1 else ''}"

        search = GoogleSearch(params)
        results = search.get_dict()
        organic_results = results.get("organic_results", [])
        return [
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "description": item.get("snippet", "")
            }
            for item in organic_results
        ]
    except Exception as e:
        print(f"Erreur lors de l'appel à SerpAPI : {e}")
        return []

@print_log_decorator
def synthesize_answer(question: str, sources: list) -> str:
    context = ""
    source_links = []
    for i, source in enumerate(sources):
        content = source["description"]
        context += f"Source {i+1} :\n{content}\n\n"
        source_links.append(f"[{i+1}] {source['link']}")

    system_prompt = f"""
    Tu es un assistant IA serviable. Ta tâche est de répondre à la question de l'utilisateur en te basant *uniquement* sur le contexte fourni par les sources web.
    N'utilise aucune connaissance préalable.
    Sois concis et réponds directement à la question.
    Liste les sources que tu as utilisées à la fin de ta réponse, formatées comme [1], [2], etc.
    La date actuelle est {datetime.now().strftime('%Y-%m-%d')}.
    
    Contexte fourni :
    {context}
    """
    try:
        response = ollama.chat(
            model='qwen2.5',
            messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': question}]
        )
        answer = response['message']['content']
        answer += "\n\n**Sources:**\n" + "\n".join(source_links)
        return answer
    except Exception as e:
        print(f"Erreur lors de la synthèse de la réponse : {e}")
        return "Je suis désolé, j'ai rencontré une erreur lors du traitement des informations."

@print_log_decorator
def save_feedback(feedback_data):
    os.makedirs("feedback", exist_ok=True)
    filename = f"feedback/feedback_{datetime.now().timestamp()}.json"
    with open(filename, "w") as f:
        json.dump(feedback_data.dict(), f, indent=4)