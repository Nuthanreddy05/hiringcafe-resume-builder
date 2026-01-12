
import os

target_file = "job_auto_submit.py"
replacement_file = "greenhouse_new.py"

with open(target_file, "r") as f:
    lines = f.readlines()

with open(replacement_file, "r") as f:
    new_code = f.read()

# Find start and end indices
start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if line.strip().startswith("def handle_greenhouse"):
        start_idx = i
    if line.strip().startswith("def handle_workday"):
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    print(f"Splicing lines {start_idx} to {end_idx}...")
    
    # We need to preserve the imports and previous code
    # insert new code
    # NOTE: The new_code string needs to ensure it has correct internal indentation, 
    # but since it's a top level function, it should be fine.
    
    final_lines = lines[:start_idx] + [new_code + "\n\n\n"] + lines[end_idx:]
    
    with open(target_file, "w") as f:
        f.writelines(final_lines)
    print("Success.")
else:
    print("Could not find function boundaries.")
