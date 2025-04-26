from flask import Flask, request, render_template, Response, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import requests
from parser import structure_protein_data
from dotenv import load_dotenv
import os
import openai


load_dotenv()
app = Flask(__name__, static_folder='../frontend', template_folder='../frontend')

CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

user_sessions = {}

DISGENET_KEY = os.getenv("DISGENET_KEY")
ALPHAFOLD_KEY = os.getenv("ALPHAFOLD_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
openai.api_key = os.getenv("openai.api_key")


def fetch_uniprot_data(name_or_id):
    url_id = f"https://rest.uniprot.org/uniprotkb/{name_or_id}.json"
    res = requests.get(url_id)
    if res.status_code == 200:
        return res.json()

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


def fetch_disgenet_diseases(gene_symbol):
    headers = {"Authorization": f"Bearer {DISGENET_KEY}"}
    url = f"https://www.disgenet.org/api/gda/gene/{gene_symbol}?source=ALL"
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        return res.json()
    return []


def fetch_ensembl_id(data):
    xrefs = data.get('uniProtKBCrossReferences', [])
    for x in xrefs:
        if x.get('database') == 'Ensembl' and x.get('id'):
            return x['id']
    return None


def fetch_protein_interactions(identifier, taxon_id):
    url = f"https://string-db.org/api/tsv/network?identifiers={identifier}&species={taxon_id}"
    res = requests.get(url)
    if res.status_code == 200:
        lines = res.text.strip().split('\n')
        if len(lines) > 1 and "preferredName_B" in lines[0]:
            return lines
    return None


def fetch_variants_clinvar(uniprot_data, protein_name):
    gene_name = ""
    genes = uniprot_data.get("genes", [])
    if genes and isinstance(genes, list):
        gene_name = genes[0].get("geneName", {}).get("value", "")

    if not gene_name:
        gene_block = uniprot_data.get("gene", {})
        gene_name = gene_block.get("geneName", {}).get("value", "")

    if not gene_name:
        gene_name = protein_name.split()[0]

    print(f"🧬 Using gene name for variants: {gene_name}")

    url = f"https://myvariant.info/v1/query?q=clinvar.rcv.conditions.name:{gene_name}&size=5"
    res = requests.get(url)

    if res.status_code == 200:
        variants = []
        for v in res.json().get("hits", []):
            var_id = v.get("_id", "N/A")
            rsid = v.get("dbsnp", {}).get("rsid", "N/A")

            clinvar_data = v.get("clinvar", {})
            rcv_list = clinvar_data.get("rcv", [])
            condition = "Unknown condition"
            if isinstance(rcv_list, list) and rcv_list:
                conditions = rcv_list[0].get("conditions", [])
                if conditions and isinstance(conditions, list):
                    condition = conditions[0]

            clinvar_link = f"https://www.ncbi.nlm.nih.gov/snp/{rsid}" if rsid != "N/A" else "#"
            variants.append(f"<a href='{clinvar_link}' target='_blank'>{rsid}</a> ({var_id}) — {condition}")

        return variants
    return []


def fetch_3d_structure(protein_id):
    alphafold_url = f"https://alphafold.ebi.ac.uk/api/prediction/{protein_id}?key={ALPHAFOLD_KEY}"
    res = requests.get(alphafold_url)
    if res.status_code == 200 and res.json():
        return f"https://alphafold.ebi.ac.uk/entry/{protein_id}"
    return None


def ask_llm(prompt, system="You are a helpful assistant that answers protein-related queries."):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("LLM Error:", e)
        return None


def fetch_protein_news(protein_name):
    NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")
    url = f"https://newsapi.org/v2/everything?q={protein_name}&language=en&sortBy=relevancy&pageSize=5&apiKey={NEWSAPI_KEY}"
    res = requests.get(url)
    if res.status_code == 200:
        articles = res.json().get("articles", [])
        if not articles:
            return ["No recent news found."]
        return [f"<a href='{a['url']}' target='_blank'>{a['title']}</a>" for a in articles]
    return ["Failed to fetch news."]




@socketio.on('user_message')
def handle_user_message(message):
    session_id = request.sid
    user_input = message.strip().lower()

    if user_input in ['function', 'functions', 'structure', 'drugs', 'diseases', 'interactions', 'variants', 'news', 'all']:
        if session_id not in user_sessions:
            emit('bot_response', {'message': "❗ Please enter a protein name or UniProt ID first!"})
            return
        data = user_sessions[session_id]
    else:
        data = fetch_uniprot_data(user_input)
        if not data:
            # Use OpenAI LLM as fallback
            answer = ask_llm(f"Answer this scientific protein-related question:\n{message}")
            if answer:
                emit('bot_response', {'message': f"🧠 {answer}"})
            else:
                emit('bot_response', {'message': "⚠️ Sorry, no data found and fallback failed."})
            return

        user_sessions[session_id] = data

        name = data.get('proteinDescription', {}).get('recommendedName', {}).get('fullName', {}).get('value', 'Name not available')
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
                       f"• Type <b>News</b><br>"
                       f"• Or type <b>All</b> for everything"
        })
        return

    name = data['proteinDescription']['recommendedName']['fullName']['value']
    functions = [t['value'] for c in data.get("comments", []) if c['commentType'] == 'FUNCTION' for t in c.get('texts', [])]

    msg_parts = [f"<b>🧬 Protein Name:</b> {name}<br>"]

    if user_input in ['function', 'functions', 'all']:
        msg_parts.append("<b>🧠 Functions:</b><br>")
        if functions:
            for func in functions:
                for sentence in func.split('. '):
                    if sentence.strip():
                        cleaned = sentence.strip()
                        if not cleaned.endswith('.'):
                            cleaned += '.'
                        msg_parts.append(f"• {cleaned}<br>")
        else:
            msg_parts.append("N/A<br>")

    if user_input in ['structure', 'all']:
        alphafold_url = fetch_3d_structure(data['primaryAccession'])
        if alphafold_url:
            msg_parts.append(
                f"<b>🧊 3D Structure:</b><br>"
                f"<a href='{alphafold_url}' target='_blank'>"
                f"<button>🔬 View in AlphaFold</button>"
                f"</a><br>"
            )
        else:
            msg_parts.append("<b>🧊 Structure:</b> Not available.<br>")

    if user_input in ['drugs', 'all']:
        drugs = fetch_chembl_drugs(name)
        msg_parts.append(f"<b>💊 Drugs (ChEMBL):</b><br> {'<br>• '.join(drugs) if drugs else 'N/A'}<br>")

    if user_input in ['diseases', 'all']:
        disease_comments = [c for c in data.get("comments", []) if c.get("commentType") == "DISEASE"]
        if disease_comments:
            msg_parts.append("<b>🦠 Diseases:</b><br>")
            for d in disease_comments:
                disease = d.get("disease", {})
                disease_id = disease.get("diseaseId", "Unnamed")
                disease_name = disease.get("acronym", "Unknown disease")
                description = disease.get("description", "No description available")
                msg_parts.append(f"• <b>{disease_name}</b> ({disease_id}): {description}<br>")
        else:
            msg_parts.append("<b>🦠 Diseases:</b><br> N/A<br>")

    if user_input in ['interactions', 'all']:
        msg_parts.append("<b>🔗 Interactions:</b><br>")
        gene_list = data.get('gene', [])
        gene_name = gene_list[0].get('geneName', {}).get('value') if gene_list else None
        taxon_id = str(data['organism']['taxonId'])
        ensembl_id = fetch_ensembl_id(data)
        interaction_data = fetch_protein_interactions(ensembl_id or gene_name, taxon_id=taxon_id)
        if interaction_data:
            top_partners = []
            for line in interaction_data[1:6]:
                fields = line.split('\t')
                if len(fields) >= 6:
                    partner_name = fields[2]
                    score = fields[5]
                    top_partners.append(f"• {partner_name} (Score: {score})<br>")
            if top_partners:
                msg_parts.extend(top_partners)
            else:
                msg_parts.append("No strong interactions found.<br>")
        else:
            msg_parts.append("❌ No interactions found in STRING DB using Ensembl ID or gene name.<br>")

    if user_input in ['variants', 'all']:
        variants = fetch_variants_clinvar(data, name)
        msg_parts.append(f"<b>🧬 Variants:</b><br>{'<br>• '.join(variants) if variants else 'N/A'}<br>")

    if user_input in ['news', 'all']:
        msg_parts.append("<b>📰 Related News:</b><br>")
        news_items = fetch_protein_news(name)
        msg_parts.append("<br>• " + "<br>• ".join(news_items) + "<br>")

    final_msg = "<br>".join(msg_parts)
    emit('bot_response', {'message': final_msg})


@app.route('/structure_viewer')
def structure_viewer():
    return render_template("structure_viewer.html")


@app.route('/get_structure/<protein_id>')
def get_structure(protein_id):
    pdb_url = f"https://files.rcsb.org/view/{protein_id}.pdb"
    response = requests.get(pdb_url)
    if response.status_code == 200:
        return Response(response.text, mimetype='text/plain')
    return Response("Access Denied or Structure Not Found", status=403)


if __name__ == '__main__':
    socketio.run(app, debug=True, use_reloader=False)