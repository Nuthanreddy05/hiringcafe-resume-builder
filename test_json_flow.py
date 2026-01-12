
import jinja2
import os
import json
from pathlib import Path

# Mock Data matching strict schema
mock_json = {
  "role_albertsons": "Senior Python Engineer",
  "role_valuelabs": "Frontend Developer",
  "experience_albertsons": [
    "Designed microservices using Python reducing latency by \\textbf{30\\%}.",
    "Collaborated with 3 teams to ship features."
  ],
  "experience_valuelabs": [
    "Built React apps for enterprise clients.",
    "Optimized SQL queries improving performance by \\textbf{20\\%}."
  ],
  "projects": [
    {
      "name": "Cloud App",
      "duration": "Jan 2024 -- May 2024",
      "bullets": [
        "Deployed on AWS.",
        "Used Docker."
      ]
    }
  ],
  "skills": [
    {"name": "Languages", "keywords": "Python, Java"},
    {"name": "Cloud", "keywords": "AWS, Azure"}
  ],
  "coursework": "Distrib Systems, ML, AI"
}

def render_test():
    template_path = os.path.abspath("resume_template.tex")
    
    try:
        env = jinja2.Environment(
            block_start_string='{%',
            block_end_string='%}',
            variable_start_string='{{',
            variable_end_string='}}',
            comment_start_string='((*',
            comment_end_string='*))',
            loader=jinja2.FileSystemLoader(os.path.dirname(template_path))
        )
        template = env.get_template(os.path.basename(template_path))
        output = template.render(**mock_json)
        
        output_path = "test_render.tex"
        with open(output_path, "w") as f:
            f.write(output)
            
        print(f"✅ Render successful! Saved to {output_path}")
        print(f"Length: {len(output)}")
        
        # Check if the hardcoded company names are present (sanity check)
        if "Albertsons" in output and "ValueLabs" in output:
             print("✅ Hardcoded Company Names Found")
        else:
             print("❌ Hardcoded Company Names MISSING")

        # Check if dynamic bullets are present
        if "Designed microservices" in output:
             print("✅ Dynamic Content Found")
        else:
             print("❌ Dynamic Content MISSING")
        
    except Exception as e:
        print(f"❌ Render failed: {e}")

if __name__ == "__main__":
    render_test()
