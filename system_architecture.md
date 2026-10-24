# Automated Answer Script Grading - System Architecture

This document provides a high-level overview of the Automated Answer Script Grading project, designed to evaluate student answer sheets automatically against provided rubrics and key answers using generative AI and NLP models.

## High-Level Workflow

```mermaid
flowchart TD
    %% Input Data
    subgraph Inputs ["Input Layer"]
        A[Student Answer Script Images] 
        B[Grading Document: sample_rubric.json]
    end

    %% Handwriting & Extraction processing
    subgraph Extraction ["1. OCR & Data Extraction Module (ocr_module.py)"]
        C[Image Loading & Error Handling]
        D[Qwen2.5-VL OCR Engine]
        E[JSON Parsing Engine]
        
        C --> D
        D -- "Extracts Handwriting, Equations & Diagrams" --> E
    end

    %% Semantic Analysis and comparative grading
    subgraph Evaluation ["2. Semantic Evaluation Module"]
        F[BERT Contextual NLP Model]
        G[Gemini-Assisted Semantic Grader]
        H[Rubric Alignment Engine]
        
        F -- "Analyzes Text Semantics" --> H
        G -- "Evaluates Logical Steps" --> H
    end

    %% Final Output Generation
    subgraph Outputs ["Output Layer"]
        I[Final Student Score]
        J[Detailed Feedback & Deductions]
    end

    %% Flow Mapping
    A --> C
    B -- "Expected Answers" --> H
    E -- "Structured Student Data (JSON)" --> F
    E --> G
    H --> I
    H --> J

    %% Styling
    classDef ai fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    class D,F,G ai;
```

## System Components

### 1. The Input Layer
- **Student Answer Scripts**: Scanned images or PDFs of the student's handwritten exam.
- **Rubrics & Key Answers**: Structured JSON configurations (like `sample_rubric.json`) that dictate the maximum marks per question, the expected answers, and the step-by-step marking logic.

### 2. OCR & Data Extraction Module
- Powered by the **Qwen2.5-VL** Vision Model (`ocr_module.py`), configurable for Dashscope API or Localhost deployment.
- Capable of reading complex handwritten text, translating equations into standard Standard LaTeX, and meticulously describing student-drawn diagrams. 
- Designed with built-in auto-retry logic to handle occasional server spikes (503 High Demand).
- Outputs exactly formatted JSON dictionaries mapping question numbers to the student's exact responses for easy downstream integration.

### 3. Semantic Evaluation Module
- Employs a dual-AI approach to grade the extracted text:
  - **Language Models (BERT/Transformers)**: Used to analyze the contextual similarity between the student's unstructured handwritten answer and the "key answer". 
  - **Generative AI (Gemini)**: Serves as the primary logic engine to determine if the student hit all the necessary semantic points outlined in the rubric (even if paraphrased).
- Accurately decides if partial credit should be awarded based on intermediate steps.

### 4. Output Layer
The architecture ultimately distills the AI evaluations into a readable format for instructors and students, providing transparent step-by-step point deductions, final scores, and actionable feedback.
