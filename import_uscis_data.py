import json
import re

def parse_raw_data(file_path):
    with open(file_path, 'r') as f:
        # Read all lines and join them, then split by company entries
        # The structure is somewhat irregular, so we need robust regex
        content = f.read()

    # Pattern to find: 
    # Rank (Number) [Tab/Space] Name [Logo?] [Tab/Space] Industry
    # [Newline]
    # 2022 [Tab] 2023 [Tab] 2024
    # [Newline]
    # Tags
    
    # We will iterate line by line
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    
    companies = []
    
    i = 0
    # Skip header row if present ("2022 2023 2024")
    if lines[0].startswith("2022"):
        i += 1
        
    while i < len(lines):
        line = lines[i]
        
        # Match Rank and Name line
        # Regex: Start with digits, then spaces, then ignores "logo", then captures Name
        # Check if line starts with a number
        match = re.match(r'^(\d+)\s+(.+?)(?:\s+logo)?\s+(.+)$', line)
        if not match:
            # Maybe just simple split?
            parts = line.split('\t')
            if len(parts) < 2:
                # Try space split but respect text?
                # Let's try flexible regex for the start
                match_flexible = re.match(r'^(\d+)\s+(.+)$', line)
                if match_flexible:
                    rank = int(match_flexible.group(1))
                    rest = match_flexible.group(2)
                    # Heuristic: Industry is usually the last tab-separated or known list?
                    # The raw data has tabs implies structured copy-paste
                    # Let's try splitting by tab
                    tab_parts = line.split('\t')
                    if len(tab_parts) >= 3:
                        rank = tab_parts[0]
                        raw_name = tab_parts[1].replace(" logo", "") # Clean logo text
                        industry = tab_parts[2] if len(tab_parts) > 2 else "Unknown"
                    else:
                        # Fallback for "1 EY logo EY Professional Services"
                        # It seems to be: Rank [tab] NameWithLogo [tab] RealName? [tab] Industry
                        # User data: "1 [tab] EY logo [tab] EY [tab] Professional Services"
                        
                        # Let's assume standard 4 line blocks or similar pattern
                        pass
        
        # Actually, let's look at the specific format provided in the prompt:
        # "1	EY logo	EY	Professional Services"
        # "633	3488	8456"
        # "Fin. - AccountingInvmt OccupationsFinancial Mgmt"
        
        # Block of 3 lines per company
        if i + 2 >= len(lines):
            break
            
        line1 = lines[i] # Rank, Name, Industry
        line2 = lines[i+1] # Stats
        line3 = lines[i+2] # Tags
        
        parts1 = line1.split('\t')
        
        try:
            rank = int(parts1[0])
            # Handle empty logo column vs name column
            # "1	EY logo	EY	Professional Services" -> 4 parts
            # "40		Open Avenues Foundation	Non-profit..." -> 4 parts (empty col 2)
            
            if len(parts1) >= 4:
                company_name = parts1[2].strip()
                if not company_name: # Fallback to col 1 if col 2 is empty? No, col 2 is name usually
                   company_name = parts1[1].replace(" logo", "").strip() 
                
                industry = parts1[3].strip()
            elif len(parts1) == 3:
                 company_name = parts1[1].replace(" logo", "").strip()
                 industry = parts1[2].strip()
            else:
                # Fallback regex
                company_name = "Unknown"
                industry = "Unknown"

            stats_parts = line2.split('\t')
            if len(stats_parts) >= 3:
                h1b_2022 = int(stats_parts[0])
                h1b_2023 = int(stats_parts[1])
                h1b_2024 = int(stats_parts[2])
            else:
                h1b_2022, h1b_2023, h1b_2024 = 0, 0, 0
            
            tags = line3 # Keep as string or split?
            
            companies.append({
                "rank": rank,
                "name": company_name,
                "industry": industry,
                "h1b_2022": h1b_2022,
                "h1b_2023": h1b_2023,
                "h1b_2024": h1b_2024,
                "tags": tags
            })
            
            i += 3 # Move to next block
            
        except ValueError:
            # If parsing fails, skip line and try to sync
            i += 1
            
    return companies

def update_json(data, json_path):
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"Successfully updated {json_path} with {len(data)} companies.")

if __name__ == "__main__":
    raw_path = "career_scraper_dashboard/raw_h1b_data.txt"
    json_path = "career_scraper_dashboard/uscis_h1b_top_list.json"
    
    data = parse_raw_data(raw_path)
    update_json(data, json_path)
