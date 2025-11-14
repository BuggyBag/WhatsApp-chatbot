from flask import Flask, request, send_from_directory
from twilio.twiml.messaging_response import MessagingResponse
from langdetect import detect
from google import genai
from google.genai import types
import datetime
import os

# Para web scraping
import requests
from bs4 import BeautifulSoup

# === CONFIGURACIÓN ===
app = Flask(__name__)

SYSTEM_PROMPT = (
    "You are Inteligencia Azteca, a friendly chatbot that knows everything about Universidad de las Américas Puebla (UDLAP). "
    "You can answer questions about admissions, faculties, student life, events, scholarships, and services. "
    "Keep answers concise, friendly, and helpful — like a student ambassador. "
)

# === UTILIDADES ===
def should_use_web_search(user_message):
    keywords = [
        "when", "where", "who", "how much", "schedule", "event", "deadline",
        "admission", "scholarship", "requirements", "cost", "faculty", "address", "date"
    ]
    return any(word.lower() in user_message.lower() for word in keywords)

def web_search_placeholder(query, max_results=3):
    """Simulate web search results for demonstration."""
    return [f"Simulated snippet {i+1} for query: {query}" for i in range(max_results)]

def detect_language_safe(text):
    try:
        return detect(text)
    except:
        return "en"


#Web Scraping function to fetch readable text from a webpage
def fetch_web_content(url, max_chars=1500):
    """Obtiene texto legible de una página web para dar contexto a Gemini."""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")

        # Eliminar scripts, estilos, y contenido innecesario
        for tag in soup(["script", "style", "noscript", "footer", "header"]):
            tag.decompose()

        text = " ".join(soup.stripped_strings)
        return text[:max_chars]  # Limitar para no sobrecargar el modelo
    except Exception as e:
        print(f"⚠️ Error al obtener {url}: {e}")
        return None


# === INTERACCIÓN CON GEMINI ===
def ask_gemini(prompt):
    client = genai.Client(api_key="AIzaSyD67ff7RlSp6GHSTpdAQpMsHHzgoarS5ic")
    content_part = types.Part.from_text(text=prompt)
    contents = [types.Content(parts=[content_part])]
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
        config=types.GenerateContentConfig(temperature=0.7)
    )
    return response.text.strip()

# === URLS RECOMENDADAS SEGÚN TEMA ===
TOPIC_URLS = {
    "admission": "https://www.udlap.mx/admisiones",
    "admisión": "https://www.udlap.mx/admisiones",
    "scholarship": "https://www.udlap.mx/becas",
    "beca": "https://www.udlap.mx/becas",
    "facultad": "https://www.udlap.mx/ofertaacademica",
    "faculty": "https://www.udlap.mx/ofertaacademica",
    "event": "https://www.udlap.mx/eventos",
    "evento": "https://www.udlap.mx/eventos",
    "costo": "https://www.udlap.mx/pagosycolegiaturas/costosycuotas",
    "vida estudiantil": "https://www.udlap.mx/vidauniversitaria",
    "servicio": "https://www.udlap.mx/servicios",
    "contacto": "https://www.udlap.mx/contacto"
}

def get_recommended_link(user_message):
    """Busca si el mensaje del usuario coincide con alguna categoría conocida."""
    for keyword, url in TOPIC_URLS.items():
        if keyword.lower() in user_message.lower():
            return url
    return None

# === GUARDAR HISTORIAL ===
CONVERSATION_FOLDER = "conversations"
os.makedirs(CONVERSATION_FOLDER, exist_ok=True)

"""
def save_conversation(user_number, user_message, bot_reply):
    folder = "conversations"
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, f"{user_number.replace(':', '_')}.txt")
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now()}\n")
        f.write(f"User: {user_message}\n")
        f.write(f"Bot: {bot_reply}\n")
        f.write("="*50 + "\n")
 """
 
def save_conversation(user_number, user_message, bot_reply):
    file_path = os.path.join(CONVERSATION_FOLDER, f"{user_number.replace(':', '_')}.txt")
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now()}\n")
        f.write(f"User: {user_message}\n")
        f.write(f"Bot: {bot_reply}\n")
        f.write("="*50 + "\n")
        
# === DESCARGAR CHAT (ruta pública) ===
@app.route("/descargar/<user_id>", methods=["GET"])
def descargar_chat(user_id):
    """Permite descargar el archivo de conversación del usuario."""
    file_name = f"{user_id}.txt"
    file_path = os.path.join(CONVERSATION_FOLDER, file_name)
    if os.path.exists(file_path):
        return send_from_directory(CONVERSATION_FOLDER, file_name, as_attachment=True)
    return "Archivo no encontrado", 404

"""
# === RUTA PRINCIPAL DE WHATSAPP ===
@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.form.get("Body", "").strip()
    user_number = request.form.get("From", "unknown")

    print(f"{user_number} -> {incoming_msg}")

    if not incoming_msg:
        return "No message", 400

    user_lang = detect_language_safe(incoming_msg)
    context = f"Respond in the same language as the user ({user_lang})."

    # Simula web search si aplica
    if should_use_web_search(incoming_msg):
        snippets = web_search_placeholder(incoming_msg)
        context += "\nWeb search results:\n" + "\n".join(snippets)

    # Crear prompt final
    prompt = SYSTEM_PROMPT + "\n" + context + "\nUser: " + incoming_msg + "\nBot:"

    # Obtener respuesta de Gemini
    try:
        bot_reply = ask_gemini(prompt)
        if not bot_reply or "no puedo" in bot_reply.lower() or "no sé" in bot_reply.lower():
            bot_reply += "\n\nPuedes obtener más información en el sitio oficial: https://www.udlap.mx/"
    except Exception as e:
        bot_reply = f"Ocurrió un error al procesar tu mensaje: {e}"

    # Guardar historial
    save_conversation(user_number, incoming_msg, bot_reply)

    # Responder al usuario
    resp = MessagingResponse()
    msg = resp.message()
    msg.body(bot_reply)
    return str(resp)
"""
    
# === WEBHOOK PRINCIPAL DE WHATSAPP ===
@app.route("/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.form.get("Body", "").strip().lower()
    user_number = request.form.get("From", "unknown").replace("whatsapp:", "")
    print(f"{user_number} -> {incoming_msg}")

    resp = MessagingResponse()
    msg = resp.message()

    #Si el usuario pide descargar su chat
    if "descargar" in incoming_msg and "chat" in incoming_msg:
        file_name = f"{user_number.replace(':', '_')}.txt"
        file_path = os.path.join(CONVERSATION_FOLDER, file_name)
        if os.path.exists(file_path):
            #Usa aquí tu URL de ngrok actual:
            download_url = f"https://TU_URL_DE_NGROK/descargar/{user_number.replace(':', '_')}"
            msg.body(f"Aquí tienes tu conversación guardada:\n{download_url}")
        else:
            msg.body("No he encontrado un historial aún. Escribe algo y vuelve a intentarlo más tarde.")
        return str(resp)

    #Si es otro mensaje, procesarlo normalmente
    user_lang = detect_language_safe(incoming_msg)
    context = f"Respond in the same language as the user ({user_lang})."

    # Simula búsqueda web si aplica
    if should_use_web_search(incoming_msg):
        snippets = web_search_placeholder(incoming_msg)
        context += "\nWeb search results:\n" + "\n".join(snippets)

    # Remplazar este bloque:
    """
    # Crear prompt final
    prompt = SYSTEM_PROMPT + "\n" + context + "\nUser: " + incoming_msg + "\nBot:"
    """
    # Crear prompt final dentro de whatsapp_webhook()
    related_url = get_recommended_link(incoming_msg) 
    web_context = ""

    if related_url:
        web_content = fetch_web_content(related_url)
        if web_content:
            web_context = f"\n\n--- Información obtenida del sitio oficial ({related_url}) ---\n{web_content}\n--- Fin del contenido web ---\n"
        else:
            web_context = f"\n(No se pudo acceder al sitio: {related_url})\n"

    # Crear prompt final con contexto del sitio oficial si aplica
    prompt = (
        SYSTEM_PROMPT
        + "\n"
        + context
        + web_context
        + "\nUser: "
        + incoming_msg
        + "\nBot:"
    )


    """
    # Obtener respuesta de Gemini
    try:
        bot_reply = ask_gemini(prompt)
        if not bot_reply or "no puedo" in bot_reply.lower() or "no sé" in bot_reply.lower():
            bot_reply += "\n\nPuedes obtener más información en el sitio oficial: https://www.udlap.mx/"
    except Exception as e:
        bot_reply = f"Ocurrió un error al procesar tu mensaje: {e}"
    """
    
    # Obtener respuesta de Gemini
    try:
        bot_reply = ask_gemini(prompt)

        # Si la respuesta es vacía o poco precisa, agrega el link general
        if not bot_reply or "no puedo" in bot_reply.lower() or "no sé" in bot_reply.lower():
            bot_reply += "\n\nPuedes obtener más información en el sitio oficial: https://www.udlap.mx/"
        else:
            # Buscar un link relacionado con el tema
            related_url = get_recommended_link(incoming_msg)
            if related_url:
                bot_reply += f"\n\nPuedes consultar más detalles en: {related_url}"

    except Exception as e:
        bot_reply = f"Ocurrió un error al procesar tu mensaje: {e}"
    
    # Guardar historial
    save_conversation(user_number, incoming_msg, bot_reply)

    # Enviar respuesta
    msg.body(bot_reply)
    return str(resp)

# === INICIO DEL SERVIDOR ===
if __name__ == "__main__":
    app.run(port=5000, debug=True)