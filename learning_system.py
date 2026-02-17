"""
Iterative Learning System - Improves Accuracy with Each Application

This system:
1. Collects all questions from every form
2. Tracks which answers work vs fail
3. Builds a "question database" automatically
4. Updates answer logic based on success patterns
"""

from pathlib import Path
import json
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict

class ApplicationLearningSystem:
    """Learns from every application to improve accuracy over time."""
    
    def __init__(self, workspace_dir: Path):
        self.workspace_dir = workspace_dir
        self.knowledge_base = workspace_dir / "application_knowledge.json"
        self.stats_file = workspace_dir / "learning_stats.json"
        
        # Load existing knowledge
        self.knowledge = self._load_knowledge()
        self.stats = self._load_stats()
    
    def record_application_attempt(self, job_name: str, questions_and_answers: List[Dict], 
                                   validation_result: Dict):
        """
        Record what happened in an application attempt.
        
        Args:
            job_name: Name of the job/company
            questions_and_answers: List of {question, ai_answer, form_accepted}
            validation_result: {success: bool, accuracy: float, errors: List}
        """
        timestamp = datetime.now().isoformat()
        
        # Update knowledge base with new questions
        for qa in questions_and_answers:
            self._learn_from_question(qa, timestamp)
        
        # Update statistics
        self.stats['total_applications'] = self.stats.get('total_applications', 0) + 1
        self.stats['total_accuracy'] = self._calculate_running_accuracy(validation_result['accuracy'])
        self.stats['last_updated'] = timestamp
        
        # Save everything
        self._save_knowledge()
        self._save_stats()
        
        # Generate improvement report
        self._print_learning_report()
    
    def _learn_from_question(self, qa: Dict, timestamp: str):
        """Learn from a single question-answer pair."""
        question = qa['question'].lower().strip()
        answer = qa['ai_answer']
        success = qa.get('form_accepted', True)
        
        # Initialize question entry if new
        if question not in self.knowledge:
            self.knowledge[question] = {
                'question_variations': [qa['question']],
                'successful_answers': defaultdict(int),
                'failed_answers': defaultdict(int),
                'total_attempts': 0,
                'success_rate': 0.0,
                'first_seen': timestamp,
                'last_seen': timestamp,
                'question_type': self._classify_question(question)
            }
        
        # Update question data
        q_data = self.knowledge[question]
        q_data['total_attempts'] += 1
        q_data['last_seen'] = timestamp
        
        # Record answer success/failure
        if success:
            q_data['successful_answers'][answer] += 1
        else:
            q_data['failed_answers'][answer] += 1
        
        # Calculate success rate
        total_success = sum(q_data['successful_answers'].values())
        q_data['success_rate'] = total_success / q_data['total_attempts']
        
        # Add question variation
        if qa['question'] not in q_data['question_variations']:
            q_data['question_variations'].append(qa['question'])
    
    def _classify_question(self, question: str) -> str:
        """Classify question type for pattern recognition."""
        q_lower = question.lower()
        
        if 'sponsor' in q_lower or 'visa' in q_lower:
            return 'sponsorship'
        elif 'gender' in q_lower:
            return 'gender'
        elif 'race' in q_lower or 'ethnicity' in q_lower:
            return 'race_ethnicity'
        elif 'veteran' in q_lower or 'military' in q_lower:
            return 'veteran_status'
        elif 'disability' in q_lower:
            return 'disability'
        elif 'salary' in q_lower or 'compensation' in q_lower:
            return 'salary'
        elif 'start' in q_lower and 'date' in q_lower:
            return 'start_date'
        elif 'authorized' in q_lower or 'legally' in q_lower:
            return 'work_authorization'
        elif 'location' in q_lower or 'city' in q_lower:
            return 'location'
        else:
            return 'other'
    
    def get_best_answer(self, question: str) -> Tuple[str, float]:
        """
        Get the best answer for a question based on historical success.
        
        Returns:
            (answer, confidence_score)
        """
        q_lower = question.lower().strip()
        
        # Check if we've seen this exact question
        if q_lower in self.knowledge:
            q_data = self.knowledge[q_lower]
            if q_data['successful_answers']:
                # Return most successful answer
                best_answer = max(q_data['successful_answers'].items(), 
                                key=lambda x: x[1])[0]
                confidence = q_data['success_rate']
                return best_answer, confidence
        
        # Check for similar questions by type
        q_type = self._classify_question(q_lower)
        similar_questions = [
            (q, data) for q, data in self.knowledge.items()
            if data['question_type'] == q_type
        ]
        
        if similar_questions:
            # Aggregate successful answers from similar questions
            answer_scores = defaultdict(float)
            for _, data in similar_questions:
                for answer, count in data['successful_answers'].items():
                    answer_scores[answer] += count * data['success_rate']
            
            if answer_scores:
                best_answer = max(answer_scores.items(), key=lambda x: x[1])[0]
                confidence = 0.7  # Medium confidence for similar questions
                return best_answer, confidence
        
        # No knowledge - return None
        return None, 0.0
    
    def get_improvement_suggestions(self) -> List[str]:
        """Generate suggestions for improving the system."""
        suggestions = []
        
        # Find low success rate questions
        problematic = [
            (q, data) for q, data in self.knowledge.items()
            if data['success_rate'] < 0.8 and data['total_attempts'] >= 3
        ]
        
        for q, data in sorted(problematic, key=lambda x: x[1]['success_rate']):
            suggestions.append({
                'question': q,
                'success_rate': data['success_rate'],
                'attempts': data['total_attempts'],
                'type': data['question_type'],
                'recommendation': f"Review answer logic for {data['question_type']} questions"
            })
        
        return suggestions
    
    def _calculate_running_accuracy(self, new_accuracy: float) -> float:
        """Calculate running average accuracy."""
        total = self.stats.get('total_applications', 0)
        current_avg = self.stats.get('total_accuracy', 0.0)
        
        if total == 0:
            return new_accuracy
        
        return ((current_avg * total) + new_accuracy) / (total + 1)
    
    def _print_learning_report(self):
        """Print current learning status."""
        print(f"\n📊 LEARNING SYSTEM REPORT")
        print(f"   Total Applications Processed: {self.stats.get('total_applications', 0)}")
        print(f"   Overall Accuracy: {self.stats.get('total_accuracy', 0)*100:.1f}%")
        print(f"   Unique Questions Learned: {len(self.knowledge)}")
        
        # Show question type breakdown
        type_counts = defaultdict(int)
        for data in self.knowledge.values():
            type_counts[data['question_type']] += 1
        
        print(f"\n   Question Types Known:")
        for q_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"      - {q_type}: {count} questions")
    
    def _load_knowledge(self) -> Dict:
        """Load existing knowledge base."""
        if self.knowledge_base.exists():
            return json.loads(self.knowledge_base.read_text())
        return {}
    
    def _save_knowledge(self):
        """Save knowledge base."""
        # Convert defaultdicts to regular dicts for JSON
        knowledge_serializable = {}
        for q, data in self.knowledge.items():
            knowledge_serializable[q] = {
                **data,
                'successful_answers': dict(data['successful_answers']),
                'failed_answers': dict(data['failed_answers'])
            }
        
        self.knowledge_base.write_text(json.dumps(knowledge_serializable, indent=2))
    
    def _load_stats(self) -> Dict:
        """Load statistics."""
        if self.stats_file.exists():
            return json.loads(self.stats_file.read_text())
        return {}
    
    def _save_stats(self):
        """Save statistics."""
        self.stats_file.write_text(json.dumps(self.stats, indent=2))


def integrate_learning_with_form_fill(page, question: str, learning_system: ApplicationLearningSystem) -> str:
    """
    Integrated answer function that uses learning system.
    
    Flow:
    1. Check if we've seen this question before
    2. If yes, use historically successful answer
    3. If no, use AI answer
    4. Record result for future learning
    """
    # Try to get answer from learned knowledge
    learned_answer, confidence = learning_system.get_best_answer(question)
    
    if learned_answer and confidence > 0.8:
        print(f"      🧠 Using learned answer (confidence: {confidence*100:.0f}%): {learned_answer}")
        return learned_answer
    else:
        # Fall back to AI
        print(f"      🤖 Using AI (new question or low confidence)")
        # Use existing answer_question_with_ai() function
        return None  # Signals to use AI


# Example usage in job_auto_submit.py:
"""
# At start of script
learning_system = ApplicationLearningSystem(Path("Google Auto Internet"))

# During form filling
for question in questions:
    # Try learned answer first
    answer = integrate_learning_with_form_fill(page, question, learning_system)
    
    if answer is None:
        # Use AI
        answer = answer_question_with_ai(question, context)
    
    # Fill the field
    fill_field(page, question, answer)
    
    # Record the attempt
    qa_record = {
        'question': question,
        'ai_answer': answer,
        'form_accepted': True  # Will be updated after validation
    }

# After form validation
learning_system.record_application_attempt(
    job_name="Company Name",
    questions_and_answers=qa_records,
    validation_result=validation_result
)
"""
