import torch
from sentence_transformers import SentenceTransformer, util

class SemanticAnalyzer:
    def __init__(self, model_name='microsoft/codebert-base'):
        """
        Initializes the semantic analyzer with a pre-trained model.
        Defaulting to a model that can handle both code (SQL/programming) and natural language.
        'sentence-transformers/all-MiniLM-L6-v2' is also a good generic text alternative.
        
        Using feature extraction pipeline for CodeBERT or sentence-transformers.
        """
        self.model_name = model_name
        print(f"Loading semantic model: {model_name}...")
        
        # We use SentenceTransformer as it provides a convenient wrapper 
        # for generating embeddings from HuggingFace models.
        # Ensure the model exists on HF Hub and is supported.
        # Fallback to 'all-MiniLM-L6-v2' for faster testing if needed.
        try:
            self.model = SentenceTransformer(model_name)
        except Exception as e:
            print(f"Failed to load {model_name}, falling back to all-MiniLM-L6-v2. Error: {e}")
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            
        print("Model loaded successfully.")

    def calculate_similarity(self, student_answer: str, key_answer: str) -> float:
        """
        Calculates the cosine similarity between the student's answer and the key answer.
        Returns a float between 0.0 and 1.0.
        """
        if not student_answer or not key_answer:
            return 0.0

        import json
        if not isinstance(student_answer, str):
            student_answer = json.dumps(student_answer, ensure_ascii=False)
        if not isinstance(key_answer, str):
            key_answer = json.dumps(key_answer, ensure_ascii=False)

        # Compute embeddings
        student_embedding = self.model.encode(student_answer, convert_to_tensor=True)
        key_embedding = self.model.encode(key_answer, convert_to_tensor=True)
        
        # Calculate cosine similarity
        cosine_scores = util.cos_sim(student_embedding, key_embedding)
        
        # Extract the scalar value and ensure it's mapped roughly [0, 1] for our use case
        score = cosine_scores[0][0].item()
        
        # Cosine similarity can technically be negative (-1 to 1), but for text semantics 
        # it's usually >= 0. Clamp it to 0-1 for absolute safety on percentages.
        normalized_score = max(0.0, min(1.0, score))
        
        return normalized_score

if __name__ == "__main__":
    # For testing standalone
    # analyzer = SemanticAnalyzer()
    # score = analyzer.calculate_similarity("SELECT * FROM users", "SELECT id, name FROM users")
    # print(f"Similarity: {score}")
    pass
