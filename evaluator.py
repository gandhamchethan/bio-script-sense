import json
import math
import os
import random
import re

from dotenv import load_dotenv
import google.generativeai as genai
import ocr_module
from semantic_module import SemanticAnalyzer
from grading_module import GradingEngine

# Load environment variables
load_dotenv()

# Initialize Google Generative AI
google_api_key = os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    print("Error: GOOGLE_API_KEY not found in .env file")
else:
    genai.configure(api_key=google_api_key)


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


def optimize_question_marks(semantic_score: float, max_marks: float, student_ans: object = "", key_ans: object = "", population_size: int = 18, generations: int = 30) -> dict:
    """Calibrate a semantic similarity score with a lightweight genetic algorithm."""
    if max_marks <= 0:
        normalized = max(0.0, min(1.0, float(semantic_score)))
        return {
            "normalized_similarity": round(normalized, 4),
            "optimized_mark": 0.0,
            "fitness": 0.0,
            "weights": {"scale": 1.0, "bias": 0.0, "curve": 1.0},
        }

    score = max(0.0, min(1.0, float(semantic_score)))
    answer_text = str(student_ans) if not isinstance(student_ans, str) else student_ans
    key_text = str(key_ans) if not isinstance(key_ans, str) else key_ans
    answer_tokens = len(re.findall(r"\S+", answer_text))
    key_tokens = len(re.findall(r"\S+", key_text))
    coverage = 0.0 if key_tokens == 0 else min(1.0, answer_tokens / max(1, key_tokens))
    target_mark = max_marks * (0.7 * score + 0.3 * coverage)
    rng = random.Random(43)

    def chromosome_fitness(chromosome):
        scale, bias, curve = chromosome
        adjusted_score = (score - bias) * scale
        adjusted_score = max(0.0, min(1.0, adjusted_score))
        calibrated_score = _sigmoid(curve * (adjusted_score - 0.5))
        predicted_mark = max_marks * (0.7 * calibrated_score + 0.3 * coverage)
        error = abs(predicted_mark - target_mark)
        penalty = abs(scale - 1.0) * 0.15 + abs(curve - 2.0) * 0.05
        return -(error + penalty)

    population = [
        [rng.uniform(0.7, 1.6), rng.uniform(-0.15, 0.15), rng.uniform(1.0, 4.5)]
        for _ in range(population_size)
    ]

    best_chromosome = max(population, key=chromosome_fitness)
    best_fitness = chromosome_fitness(best_chromosome)

    for _ in range(generations):
        ranked_population = sorted(population, key=chromosome_fitness, reverse=True)
        elite_count = max(2, population_size // 2)
        next_population = ranked_population[:elite_count]

        while len(next_population) < population_size:
            parent_a, parent_b = rng.sample(ranked_population[:max(2, elite_count)], 2)
            child = []
            for idx in range(3):
                if rng.random() < 0.5:
                    gene = parent_a[idx]
                else:
                    gene = parent_b[idx]
                if rng.random() < 0.35:
                    gene += rng.uniform(-0.2, 0.2)
                if idx == 0:
                    gene = max(0.4, min(2.0, gene))
                elif idx == 1:
                    gene = max(-0.3, min(0.3, gene))
                else:
                    gene = max(0.5, min(6.0, gene))
                child.append(gene)
            next_population.append(child)

        population = next_population
        candidate = max(population, key=chromosome_fitness)
        candidate_fitness = chromosome_fitness(candidate)
        if candidate_fitness > best_fitness:
            best_chromosome = candidate
            best_fitness = candidate_fitness

    scale, bias, curve = best_chromosome
    adjusted_score = (score - bias) * scale
    adjusted_score = max(0.0, min(1.0, adjusted_score))
    normalized_similarity = max(0.0, min(1.0, _sigmoid(curve * (adjusted_score - 0.5))))
    optimized_mark = max_marks * (0.7 * normalized_similarity + 0.3 * coverage)

    return {
        "normalized_similarity": round(normalized_similarity, 4),
        "optimized_mark": round(optimized_mark, 2),
        "fitness": round(best_fitness, 4),
        "weights": {
            "scale": round(scale, 4),
            "bias": round(bias, 4),
            "curve": round(curve, 4),
        },
    }


def run_evaluation(image_path: str, key_answers_file: str, rubrics_file: str):
    print("=== AI Answer Script Evaluator ===")
    
    # Check inputs
    if not os.path.exists(image_path):
        error_msg = f"Error: Could not find image at {image_path}"
        print(error_msg)
        return {"error": error_msg}
        
    try:
        with open(key_answers_file, 'r', encoding='utf-8') as f:
            key_answers = json.load(f)
        with open(rubrics_file, 'r', encoding='utf-8') as f:
            rubrics = json.load(f)
    except Exception as e:
        error_msg = f"Error loading JSON configuration: {e}"
        print(error_msg)
        return {"error": error_msg}

    # 1. OCR / Answer Input Phase
    if image_path.lower().endswith('.json'):
        print("\n[1/3] Loading pre-extracted OCR JSON file...")
        try:
            with open(image_path, 'r', encoding='utf-8') as f:
                student_answers = json.load(f)
        except Exception as e:
            error_msg = f"Failed to load student answer JSON: {e}"
            print(error_msg)
            return {"error": error_msg}
    else:
        print("\n[1/3] Extracting text from answer script image/PDF...")
        try:
            student_answers = ocr_module.process_answerscript(image_path)
        except Exception as e:
            error_msg = f"OCR Failed: {e}"
            print(error_msg)
            return {"error": error_msg}

    print(f"Loaded {len(student_answers)} student answer entry/entries successfully.")

    # 2. Initialization of Analysis Tools
    print("\n[2/3] Initializing Semantic Analyzer and Grading Engine...")
    # Using CodeBERT per user requirement for handling SQL/Code as well as text
    analyzer = SemanticAnalyzer(model_name='microsoft/codebert-base')
    grader = GradingEngine()

    results = {}
    total_awarded = 0.0
    total_max = 0.0

    print("\n[3/3] Evaluating Answers...")
    # 3. Main Loop
    for q_id, student_ans in student_answers.items():
        print(f"Evaluating Question {q_id}...")
        
        # In case the OCR picks up a question not in the key/rubric
        if q_id not in key_answers or q_id not in rubrics:
            print(f"  Warning: Question '{q_id}' not found in key answers or rubrics. Skipping.")
            continue
            
        key_ans = key_answers[q_id]
        rubric = rubrics[q_id]
        
        # A. Semantic Analysis
        score = analyzer.calculate_similarity(student_ans, key_ans)

        # B. Genetic optimization to calibrate the semantic score before grading
        optimization = optimize_question_marks(score, rubric.get('max_marks', 0), student_ans, key_ans)
        calibrated_score = optimization['normalized_similarity']

        # C. Grading and Feedback Calculation
        evaluation = grader.generate_feedback_and_marks(q_id, student_ans, key_ans, rubric, calibrated_score)

        evaluation['student_answer'] = student_ans
        evaluation['genetic_optimization'] = {
            'raw_semantic_score': round(score, 4),
            'optimized_semantic_score': optimization['normalized_similarity'],
            'optimized_mark': optimization['optimized_mark'],
            'fitness': optimization['fitness'],
            'weights': optimization['weights'],
        }
        results[q_id] = evaluation
        
        total_awarded += evaluation['awarded_marks']
        total_max += rubric.get('max_marks', 0)

    # 4. Compile and output results
    final_report = {
        "final_score": f"{total_awarded}/{total_max}",
        "percentage": round((total_awarded / total_max) * 100, 2) if total_max > 0 else 0,
        "section_breakdown": results
    }

    print("\n=== FINAL EVALUATION REPORT ===")
    print(json.dumps(final_report, indent=4))
    
    # Save the report
    with open('evaluation_report.json', 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=4, ensure_ascii=False)
    print("Report saved to evaluation_report.json")
    return final_report

if __name__ == '__main__':
    # Usage example
    import sys
    if len(sys.argv) == 4:
        # python evaluator.py <image_path> <key.json> <rubric.json>
        run_evaluation(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python evaluator.py <path_to_answerscript_image> <path_to_keys_json> <path_to_rubrics_json>")
        print("Falling back to default paths (sample.jpg, sample_key.json, sample_rubric.json)")
        run_evaluation('sample.jpg', 'sample_key.json', 'sample_rubric.json')
