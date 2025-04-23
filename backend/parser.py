# backend/parser.py

import re
from collections import defaultdict

def structure_protein_data(raw_text):
    patterns = {
        'GO Process': r'GO:00\d{5,8}[a-zA-Z0-9\s\-–,()]+',
        'GO Function': r'GO:00\d{5,8}[a-zA-Z0-9\s\-–,()]+',
        'GO Component': r'GO:00\d{5,8}[a-zA-Z0-9\s\-–,()]+',
        'UniProt': r'UniProt[A-Z0-9]+',
        'HGNC': r'HGNC:\d+',
        'Pfam': r'PF\d{5}',
        'InterPro': r'IPR\d{6}',
        'Reactome': r'R-HSA-\d+',
        'PDB': r'[A-Z0-9]{4}PDB',
        'PANTHER': r'PTHR\d+(?::SF\d+)?',
        'Pharos': r'Pharos[A-Z0-9]+',
        'EC_NUMBER': r'EC_NUMBER[\d.]+',
        'Protein Names': r'(Probable ATP-dependent RNA helicase [A-Z0-9\-]+)'
    }

    data = defaultdict(list)

    for label, pattern in patterns.items():
        matches = re.findall(pattern, raw_text)
        if matches:
            clean_matches = list(set(m.strip() for m in matches))
            data[label].extend(clean_matches)

    return dict(data)
