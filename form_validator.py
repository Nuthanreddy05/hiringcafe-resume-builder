"""
Form Validation and Feedback System
Verifies that form fields are filled correctly and logs errors for improvement.
"""

from pathlib import Path
from playwright.sync_api import Page
import json
from datetime import datetime
from typing import Dict, List, Tuple

class FormValidator:
    """Validates form fills and provides feedback for improvement."""
    
    def __init__(self, job_dir: Path):
        self.job_dir = job_dir
        self.errors_log = job_dir / "fill_errors.json"
        self.validation_report = job_dir / "validation_report.json"
        
    def verify_greenhouse_form(self, page: Page, expected_values: Dict[str, str]) -> Tuple[bool, List[Dict]]:
        """
        Verify that Greenhouse form was filled correctly.
        
        Returns:
            (success: bool, errors: List[Dict])
        """
        errors = []
        
        # Check all input fields
        inputs = page.locator("input[type='text'], input[type='email'], input[type='tel']").all()
        
        for inp in inputs:
            try:
                # Get field identifier
                field_id = inp.get_attribute("id") or ""
                field_name = inp.get_attribute("name") or ""
                field_label = self._get_label_for_input(page, inp)
                
                # Get actual value
                actual_value = inp.input_value()
                
                # Check against expected
                expected = self._find_expected_value(field_label, expected_values)
                
                if expected and actual_value != expected:
                    errors.append({
                        "field": field_label,
                        "expected": expected,
                        "actual": actual_value,
                        "field_id": field_id,
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                continue
        
        # Check dropdowns/selects
        selects = page.locator("select, div[class*='select']").all()
        
        for select in selects:
            try:
                field_label = self._get_label_for_input(page, select)
                
                # Get selected value
                actual_value = self._get_select_value(page, select)
                expected = self._find_expected_value(field_label, expected_values)
                
                if expected and actual_value != expected:
                    errors.append({
                        "field": field_label,
                        "expected": expected,
                        "actual": actual_value,
                        "type": "dropdown",
                        "timestamp": datetime.now().isoformat()
                    })
            except Exception as e:
                continue
        
        # Log errors
        if errors:
            self._log_errors(errors)
        
        # Generate report
        success = len(errors) == 0
        self._generate_report(success, len(inputs) + len(selects), errors)
        
        return success, errors
    
    def _get_label_for_input(self, page: Page, element) -> str:
        """Get label text for an input element."""
        try:
            # Try to find associated label
            field_id = element.get_attribute("id")
            if field_id:
                label = page.locator(f"label[for='{field_id}']").first
                if label.count() > 0:
                    return label.inner_text()
            
            # Try parent label
            parent = element.locator("xpath=../..")
            label = parent.locator("label").first
            if label.count() > 0:
                return label.inner_text()
            
            return "Unknown Field"
        except:
            return "Unknown Field"
    
    def _get_select_value(self, page: Page, select) -> str:
        """Get selected value from dropdown."""
        try:
            # For standard select
            if select.get_attribute("tagName") == "SELECT":
                return select.input_value()
            
            # For React-Select
            selected_text = select.locator("div[class*='singleValue']").first
            if selected_text.count() > 0:
                return selected_text.inner_text()
            
            return ""
        except:
            return ""
    
    def _find_expected_value(self, field_label: str, expected_values: Dict[str, str]) -> str:
        """Find expected value for a field based on label."""
        field_lower = field_label.lower()
        
        # Direct match
        if field_label in expected_values:
            return expected_values[field_label]
        
        # Fuzzy match
        for key, value in expected_values.items():
            if key.lower() in field_lower or field_lower in key.lower():
                return value
        
        return ""
    
    def _log_errors(self, errors: List[Dict]):
        """Log errors to file for analysis."""
        existing_errors = []
        if self.errors_log.exists():
            existing_errors = json.loads(self.errors_log.read_text())
        
        existing_errors.extend(errors)
        
        self.errors_log.write_text(json.dumps(existing_errors, indent=2))
    
    def _generate_report(self, success: bool, total_fields: int, errors: List[Dict]):
        """Generate validation report."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "success": success,
            "total_fields": total_fields,
            "error_count": len(errors),
            "accuracy": (total_fields - len(errors)) / total_fields if total_fields > 0 else 0,
            "errors": errors
        }
        
        self.validation_report.write_text(json.dumps(report, indent=2))
        
        print(f"\n📊 VALIDATION REPORT:")
        print(f"   Total Fields: {total_fields}")
        print(f"   Errors: {len(errors)}")
        print(f"   Accuracy: {report['accuracy']*100:.1f}%")
        
        if errors:
            print(f"\n⚠️  ERRORS FOUND:")
            for err in errors:
                print(f"   - {err['field']}: Expected '{err['expected']}', Got '{err['actual']}'")
    
    def get_improvement_suggestions(self) -> List[str]:
        """Analyze errors and suggest improvements."""
        if not self.errors_log.exists():
            return []
        
        errors = json.loads(self.errors_log.read_text())
        
        # Group errors by field
        error_counts = {}
        for err in errors:
            field = err.get("field", "Unknown")
            error_counts[field] = error_counts.get(field, 0) + 1
        
        # Generate suggestions
        suggestions = []
        for field, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
            suggestions.append(f"Field '{field}' failed {count} times - review AI logic for this question type")
        
        return suggestions


def build_expected_values(profile: Dict) -> Dict[str, str]:
    """Build expected values from profile for validation."""
    return {
        "First Name": profile.get("first_name", ""),
        "Last Name": profile.get("last_name", ""),
        "Email": profile.get("email", ""),
        "Phone": profile.get("phone", ""),
        "LinkedIn Profile": profile.get("linkedin", ""),
        "Salary": "$100,000 - $120,000",
        "Gender": "Male",
        "Race & Ethnicity": "Asian",
        "Military status": "I am not a protected veteran",
        "Sponsorship": "No",
        "Russian": "No",
        "Location": "No"  # For "Are you in Spain/Portugal" type questions
    }
