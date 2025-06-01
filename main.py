from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import random
import requests
from openai import OpenAI

app = Flask(__name__)
CORS(app)

# Chargement des clés API
openai_api_key = os.getenv("OPENAI_API_KEY")
eleven_api_key = os.getenv("ELEVEN_API_KEY")
voice_id = "bozffAqAkoP5Lp5FKAyE"
client = OpenAI(api_key=openai_api_key)
surnom = "Lili"
messages_by_user = {}

# Log des clés pour debug (à commenter en prod)
print("🔑 Clé OpenAI présente :", bool(openai_api_key))
print("🔑 Clé ElevenLabs présente :", bool(eleven_api_key))

questions_emo = [
    "Et toi, comment tu te sens aujourd’hui ?",
    "Tu veux me raconter un moment où tu as été fier(e) de toi aujourd'hui ?",
    "Si tu étais une météo aujourd’hui, tu serais plutôt soleil, nuage ou pluie ?",
    "Est-ce qu’il y a quelque chose qui t’a rendu(e) très content(e) ou un peu triste ?",
]

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    name = data.get("name")
    user_message = data.get("message")

    if not name or not user_message:
        return jsonify({"error": "Missing name or message"}), 400

    if name not in messages_by_user:
        messages_by_user[name] = [{
            "role": "system",
            "content": f"""Tu es un assistant éducatif bienveillant qui discute avec un enfant nommé {name}.
Tu t’appelles {surnom}. Tu l’aides à apprendre des choses de manière ludique, douce et rassurante.
Tu peux aussi raconter des histoires simples et magiques quand on te le demande.
Tu poses parfois des questions pour comprendre ses émotions et tu mémorises un peu ce qu’il te dit.
Sois chaleureux, encourageant et très accessible."""
        }]

    messages = messages_by_user[name]
    messages.append({"role": "user", "content": user_message})

    if len([m for m in messages if m["role"] == "user"]) % 3 == 0:
        emotion = random.choice(questions_emo)
        messages.append({"role": "assistant", "content": emotion})

    # Appel OpenAI
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    answer = response.choices[0].message.content
    messages.append({"role": "assistant", "content": answer})

    print("🤖 Réponse GPT :", answer)

    audio_url = elevenlabs_speak(answer, name)
    return jsonify({"text": answer, "audio_url": audio_url})


def elevenlabs_speak(text, user_id="output"):
    print("🗣️ Texte envoyé à ElevenLabs :", text)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": eleven_api_key,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.8
        }
    }
    response = requests.post(url, json=data, headers=headers)

    print("🔁 Statut ElevenLabs :", response.status_code)

    if response.status_code == 200:
        os.makedirs("static", exist_ok=True)
        filename = f"static/{user_id}.mp3"
        with open(filename, "wb") as f:
            f.write(response.content)

        base_url = "yippee-backend-cozb.onrender.com"
        audio_url = f"https://{base_url}/{filename}"
        print("✅ Audio généré :", audio_url)
        return audio_url
    else:
        print("❌ Erreur ElevenLabs :", response.text)
        return ""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)
