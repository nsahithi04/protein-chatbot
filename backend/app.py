from flask import Flask, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import requests

from parser import structure_protein_data


app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

user_sessions = {}

@socketio.on('user_message')
def handle_user_message(message):
    session_id = request.sid
    user_input = message.strip().lower()
    
    def fetch_uniprot_data(name_or_id):
        # First, try UniProt ID
        url_id = f"https://rest.uniprot.org/uniprotkb/{name_or_id}.json"
        res = requests.get(url_id)
        if res.status_code == 200:
            return res.json()

        # Try name search if ID fails
        search_url = f"https://rest.uniprot.org/uniprotkb/search?query={name_or_id}&format=json&size=1"
        res = requests.get(search_url)
        if res.status_code == 200 and res.json().get("results"):
            best_match_id = res.json()['results'][0]['primaryAccession']
            res = requests.get(f"https://rest.uniprot.org/uniprotkb/{best_match_id}.json")
            return res.json() if res.status_code == 200 else None
        return None

    def fetch_chembl_drugs(protein_name):
        url = f"https://www.ebi.ac.uk/chembl/api/data/target/search.json?q={protein_name}"
        res = requests.get(url)
        if res.status_code != 200:
            return []

        targets = res.json().get('targets', [])
        if not targets:
            return []

        chembl_id = targets[0].get('target_chembl_id')
        if not chembl_id:
            return []

        activity_url = f"https://www.ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id={chembl_id}&limit=5"
        res = requests.get(activity_url)
        if res.status_code != 200:
            return []

        activities = res.json().get('activities', [])
        drugs = [a.get('molecule_chembl_id', 'N/A') for a in activities]
        return list(set(drugs))

    def fetch_disease_data(protein_id):
        url = f"https://rest.uniprot.org/uniprotkb/{protein_id}/diseases.json"
        res = requests.get(url)
        if res.status_code == 200:
            return res.json().get('diseases', [])
        return []

    def fetch_protein_interactions(protein_id):
        url = f"https://string-db.org/api/tsv/network?identifiers={protein_id}&species=9606"
        res = requests.get(url)
        if res.status_code == 200:
            return res.text
        return None

    # Check if user is asking for more info on an existing protein
    if user_input in ['function', 'functions', 'structure', 'drugs', 'diseases', 'interactions', 'variants', 'all']:
        if session_id not in user_sessions:
            emit('bot_response', {'message': "❗ Please enter a protein name or UniProt ID first!"})
            return
        data = user_sessions[session_id]
    else:
        # Treat it as new protein input
        data = fetch_uniprot_data(user_input)
        if not data:
            emit('bot_response', {'message': f"❌ Could not find '{message}' in UniProt!"})
            return
        user_sessions[session_id] = data  # Save for future queries

        name = data['proteinDescription']['recommendedName']['fullName']['value']
        organism = data['organism']['scientificName']
        emit('bot_response', {
            'message': f"🧬 <b>Protein Found!</b><br>"
                       f"<b>Name:</b> {name}<br>"
                       f"<b>Organism:</b> {organism}<br><br>"
                       f"🤔 What would you like to explore?<br>"
                       f"• Type <b>Function</b><br>"
                       f"• Type <b>Structure</b><br>"
                       f"• Type <b>Drugs</b><br>"
                       f"• Type <b>Diseases</b><br>"
                       f"• Type <b>Interactions</b><br>"
                       f"• Type <b>Variants</b><br>"
                       f"• Or type <b>All</b> for everything"
        })
        return

    # Extract info based on user choice
    name = data['proteinDescription']['recommendedName']['fullName']['value']
    sequence = data['sequence']['value']
    functions = []
    for c in data.get("comments", []):
        if c['commentType'] == 'FUNCTION':
            functions.extend([t['value'] for t in c.get('texts', [])])

    msg_parts = [f"<b>🧬 Protein Name:</b> {name}<br>"]

    if user_input in ['function', 'functions', 'all']:
        msg_parts.append("<b>🧠 Functions:</b><br>")
        if functions:
            for func in functions:
            # Break long sentences into bullets
                sentences = func.split('. ')
                for sentence in sentences:
                    if sentence.strip():
                    # Ensure the sentence ends with a period
                        cleaned = sentence.strip()
                        if not cleaned.endswith('.'):
                            cleaned += '.'
                        msg_parts.append(f"• {cleaned}<br>")
        else:
            msg_parts.append("N/A<br>")


    if user_input in ['structure', 'all']:
        msg_parts.append(f"<b>🧊 Structure (AlphaFold):</b> "
                         f"<a href='https://alphafold.ebi.ac.uk/entry/{data['primaryAccession']}' target='_blank'>View 3D Structure</a><br>")

    if user_input in ['drugs', 'all']:
        drugs = fetch_chembl_drugs(name)
        msg_parts.append(f"<b>💊 Drugs (ChEMBL):</b><br> {'<br>• '.join(drugs) if drugs else 'N/A'}<br>")

    if user_input in ['diseases', 'all']:
        diseases = fetch_disease_data(data['primaryAccession'])
        msg_parts.append(f"<b>🦠 Diseases:</b><br> {'<br>• '.join(d['diseaseId'] for d in diseases) if diseases else 'N/A'}<br>")

    if user_input in ['interactions', 'all']:
        interactions = fetch_protein_interactions(data['primaryAccession'])
        if interactions:
            msg_parts.append(f"<b>🔗 Interactions:</b><br><a href='https://string-db.org/network/{data['primaryAccession']}'>View on STRING DB</a><br>")

    if user_input in ['variants', 'all']:
        msg_parts.append("🧬 Variant data is currently under development 💡")

    final_msg = "<br>".join(msg_parts)
    emit('bot_response', {'message': final_msg})

if __name__ == '__main__':
    socketio.run(app, debug=True)

