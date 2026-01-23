import os
import subprocess
import jinja2
from pathlib import Path
from typing import Dict, Any

class PDFCompiler:
    """
    Handles Latex Compilation using Tectonic.
    """
    
    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            block_start_string='{%',
            block_end_string='%}',
            variable_start_string='{{',
            variable_end_string='}}',
            comment_start_string='((*',
            comment_end_string='*))',
            autoescape=False,
        )

    def _escape_latex(self, text: str) -> str:
        """
        Smart Escape: Only escape special chars if they are NOT already escaped.
        Preserves model's valid LaTeX (e.g. \\textbf{...}, \\%) while fixing mistakes (e.g. C#, C&C).
        """
        if not isinstance(text, str): return text
        
        import re
        # Escape #, &, _, $, % if not preceded by \
        # Pattern: (?<!\\)([#&_$%]) -> match group 1 if not preceded by backslash
        # Replacement: \\\1 -> backslash + group 1
        return re.sub(r'(?<!\\)([#&_$%])', r'\\\1', text)

    def _recursive_escape(self, data):
        if isinstance(data, dict):
            return {k: self._recursive_escape(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._recursive_escape(v) for v in data]
        elif isinstance(data, str):
            return self._escape_latex(data)
        else:
            return data

    def compile(self, resume_json: Dict[str, Any], output_path: Path, template_name: str = "template.tex") -> bool:
        """
        Render LaTeX -> Compile PDF -> Save to output_path.
        """
        try:
            # 0. Escape Data for LaTeX (Smart Escape)
            escaped_json = self._recursive_escape(resume_json)
            
            # 1. Render LaTeX
            template = self.env.get_template(template_name)
            latex_content = template.render(**escaped_json)
            
            # Save .tex file for debugging
            tex_path = output_path.with_suffix(".tex")
            tex_path.write_text(latex_content, encoding="utf-8")
            
            # 2. Compile with Tectonic
            # tectonic -X compile input.tex -o output_dir
            cmd = [
                "tectonic",
                "-X", "compile",
                str(tex_path),
                "--outdir", str(output_path.parent)
            ]
            
            # Capture output
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                print(f"❌ Tectonic Compilation Failed:\n{result.stderr}")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ PDF Compilation Error: {e}")
            return False
