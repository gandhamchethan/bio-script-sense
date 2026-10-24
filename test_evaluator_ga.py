from evaluator import optimize_question_marks


def test_optimize_question_marks_returns_valid_range():
    result = optimize_question_marks(0.82, 5, "This is a long answer with key terms and explanation.", "This is the expected answer with key terms and explanation.")

    assert 0.0 <= result["normalized_similarity"] <= 1.0
    assert 0.0 <= result["optimized_mark"] <= 5.0
    assert "fitness" in result
    assert "weights" in result
