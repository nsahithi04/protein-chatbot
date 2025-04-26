# 🧬 Protein Chatbot

This is a real-time chatbot application that allows users to explore information about proteins — such as structure, function, associated diseases, drugs, and variants — by querying databases like UniProt, AlphaFold, DisGeNET, ChEMBL, and MyVariant.info.

---

## Features

- Real-time chatbot interface using Flask-SocketIO
- Fetch protein info using UniProt
- Get 3D structure from AlphaFold
- Disease associations from DisGeNET
- Drug interactions from ChEMBL
- Gene variant data from MyVariant.info
- Protein interaction networks from STRING DB
- Secure API key handling via `.env`

---

## Requirements

Install dependencies with:

```bash
pip install -r requirements.txt
```

### requirements.txt includes:

```
Flask
flask-cors
flask-socketio
requests
python-dotenv
eventlet
```

---

## Project Structure

```
protein-chatbot/
├── backend/
│   ├── app.py
│   ├── parser.py
├── frontend/
│   ├── assets
│   │  ├── bg-pattern.svg
│   │  ├── protein-emoji.png
│   │  └── starry-night.jpg
│   ├── chat.html
│   ├── index.html
│   ├── indexstyle.css
│   ├── script.js
│   └── style.css
├── .env
└── requirements.txt
```

---

## Environment Variables

Create a `.env` file in the `protein-chatbot` directory:

> ⚠️ Make sure `.env` is in your `.gitignore` to prevent committing secrets.

---

## Running the App

### Option 1: Run directly

```bash
cd backend
python app.py
```

Then open your browser and go to: [frontend/index.html]

---

## Example Query

1. Enter a protein name or UniProt ID (e.g., `P69905` or `hemoglobin`)
2. Type:
   - `structure` → view in AlphaFold
   - `function`, `drugs`, `diseases`, `interactions`, `variants`, `news`, or `all`

---

## Viewer Example

3D structures are viewed using the AlphaFold link or embedded viewer powered by Mol\*.

---
