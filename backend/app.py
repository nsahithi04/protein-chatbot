from flask import Flask
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import requests

app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('user_message')
def handle_user_message(message):
    print(f"🔍 User asked about: {message}")

    protein_input = message.strip()

    def fetch_data_by_id(protein_id):
        url = f"https://rest.uniprot.org/uniprotkb/{protein_id}.json"
        response = requests.get(url)
        return response if response.status_code == 200 else None

    def fetch_data_by_name(name):
        query_url = f"https://rest.uniprot.org/uniprotkb/search?query={name}&format=json&size=1"
        res = requests.get(query_url)
        if res.status_code != 200 or not res.json().get('results'):
            return None
        best_match_id = res.json()['results'][0]['primaryAccession']
        return fetch_data_by_id(best_match_id)

    # First try as ID
    response = fetch_data_by_id(protein_input.upper())
    if not response:
        # Try as name
        response = fetch_data_by_name(protein_input)

    if not response:
        emit('bot_response', {'message': f"❌ Protein '{protein_input}' not found!"})
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

        reply = (
            f"🧬 <b>Protein Name</b>: {name}<br><br>"
            f"🔬 <b>Organism</b>: {organism}<br><br>"
            f"📜 <b>Function(s)</b>: {'<br>• ' + '<br>• '.join(functions) if functions else 'N/A'}<br><br>"
            f"🔗 <b>Sequence Length</b>: {len(sequence)} amino acids<br><br>"
            f"🆔 <b>UniProt ID</b>: {data['primaryAccession']}"
        )

        emit('bot_response', {'message': reply})
    
    except KeyError as e:
        emit('bot_response', {'message': f"⚠️ Error: Missing field {str(e)}"})

if __name__ == '__main__':
    socketio.run(app, debug=True)

