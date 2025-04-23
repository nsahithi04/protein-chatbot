from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import requests

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('user_message')
def handle_user_message(message):
    print(f"🔍 User asked about: {message}")  # Debug

    protein_id = message.strip().upper()
    url = f"https://rest.uniprot.org/uniprotkb/{protein_id}.json"
    response = requests.get(url)

    if response.status_code != 200:
        emit('bot_response', {'message': f"❌ Protein '{protein_id}' not found!"})
        return

    data = response.json()

    try:
        name = data['proteinDescription']['recommendedName']['fullName']['value']
        sequence = data['sequence']['value']
        organism = data['organism']['scientificName']
        functions = []

        for comment in data.get('comments', []):
            if comment['commentType'] == 'FUNCTION':
                for text in comment['texts']:
                    functions.append(text['value'])

        reply = f"""
🧬 <b>Protein Name</b>: {name}<br><br>
🔬 <b>Organism</b>: {organism}<br><br>
📜 <b>Function(s)</b>:<br>• {'<br>• '.join(functions) if functions else 'N/A'}<br><br>
🔗 <b>Sequence Length</b>: {len(sequence)} amino acids<br><br>
🆔 <b>UniProt ID</b>: {protein_id}
"""

        emit('bot_response', {'message': reply})

    except KeyError as e:
        emit('bot_response', {'message': f"⚠️ Error: Missing field {str(e)}"})

if __name__ == '__main__':
    socketio.run(app, debug=True)

