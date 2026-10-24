import google.generativeai as genai
import json
import re

class GradingEngine:
    def __init__(self):
        # Assumes genai is already configured in the main loop or ocr_engine
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def generate_feedback_and_marks(self, question_id: str, student_ans: str, key_ans: str, rubric: dict, semantic_score: float) -> dict:
        """
        Takes the answers and semantic score, uses Gemini to generate a tailored response.
        Rubric structure expected: {'max_marks': int, 'criteria': str}
        """
        max_marks = rubric.get('max_marks', 0)
        
        # Calculate a baseline mark based directly on semantic similarity
        baseline_mark = round(max_marks * semantic_score, 1)

        import time
        if not isinstance(student_ans, str):
            student_ans = json.dumps(student_ans, ensure_ascii=False)
        if not isinstance(key_ans, str):
            key_ans = json.dumps(key_ans, ensure_ascii=False)

        prompt = f"""
        You are an AI teaching assistant grading a student's answer.
        
        Question ID: {question_id}
        Maximum Marks: {max_marks}
        Grading Criteria/Rubric: {rubric.get('criteria', 'None provided')}
        
        Key Answer / Expected Answer:
        {key_ans}
        
        Student's Extracted Answer:
        {student_ans}
        
        Baseline Semantic Similarity Score (0 to 1): {semantic_score}
        Baseline Calculated Mark: {baseline_mark} out of {max_marks}

        Your Task:
        1. Review the student's answer against the key answer and rubric.
        2. Determine the final marks to award (you may adjust the baseline mark slightly if you notice the semantic score missed key details or was overly harsh).
        3. Provide short, constructive feedback to the student, specifically stating why marks were deducted based on differences between their answer and the key answer. If full marks are awarded, provide brief positive feedback.

        CRITICAL: Respond ONLY in the following JSON format:
        {{
            "awarded_marks": <float>,
            "feedback": "<string>"
        }}
        """

        for attempt in range(3):
            try:
                response = self.model.generate_content(prompt)
                text_response = response.text
                clean_json = re.sub(r'^```json\s*', '', text_response, flags=re.IGNORECASE)
                clean_json = re.sub(r'\s*```$', '', clean_json).strip()
                
                result = json.loads(clean_json)
                result['semantic_score'] = round(semantic_score, 2)
                return result
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "quota" in err_str.lower():
                    time.sleep(4)
                    continue
                print(f"Failed to generate feedback for {question_id}: {e}")
                break

        return {
            "awarded_marks": baseline_mark,
            "feedback": "Evaluated based on semantic similarity criteria.",
            "semantic_score": round(semantic_score, 2)
        }

if __name__ == "__main__":
    pass
