import json
import os

COMPANIES_FILE = os.path.join(os.path.dirname(__file__), 'companies.json')

def get_targets():
    """Load the list of target companies."""
    try:
        with open(COMPANIES_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {COMPANIES_FILE} not found.")
        return []

if __name__ == "__main__":
    targets = get_targets()
    print(f"Loaded {len(targets)} targets.")
