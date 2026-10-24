import os
import time
from dotenv import load_dotenv

# Load environment variables FIRST before importing anything else
load_dotenv()

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import evaluator

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/evaluate', methods=['POST'])
def evaluate_submission():
    # Check for answer script (either PDF/Image answerpaper OR OCR extracted JSON file)
    has_answerpaper = 'answerpaper' in request.files and request.files['answerpaper'].filename != ''
    has_ocr_json = 'ocr_json' in request.files and request.files['ocr_json'].filename != ''
    
    if not (has_answerpaper or has_ocr_json):
        return jsonify({'error': 'Please upload either a Scanned Answer Paper (PDF/Image) or an OCR Extracted JSON file.'}), 400

    if 'keys' not in request.files or request.files['keys'].filename == '':
        return jsonify({'error': 'Missing Key Answer Sheet (JSON).'}), 400

    if 'rubrics' not in request.files or request.files['rubrics'].filename == '':
        return jsonify({'error': 'Missing Rubrics File (JSON).'}), 400

    try:
        ts = int(time.time())
        # Save Answer Script file (either PDF/Image or JSON)
        if has_ocr_json:
            ans_file = request.files['ocr_json']
        else:
            ans_file = request.files['answerpaper']

        ap_filename = secure_filename(ans_file.filename)
        ap_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{ts}_{ap_filename}")
        ans_file.save(ap_path)

        keys_file = request.files['keys']
        keys_filename = secure_filename(keys_file.filename)
        keys_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{ts}_{keys_filename}")
        keys_file.save(keys_path)

        rubrics_file = request.files['rubrics']
        rubrics_filename = secure_filename(rubrics_file.filename)
        rubrics_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{ts}_{rubrics_filename}")
        rubrics_file.save(rubrics_path)

        # Run evaluation
        print(f"Running evaluation on {ap_path}, {keys_path}, {rubrics_path}")
        result = evaluator.run_evaluation(ap_path, keys_path, rubrics_path)
        
        if result is None or (isinstance(result, dict) and 'error' in result):
            error_msg = result.get('error', 'Evaluation failed. Check server logs.') if result else 'Evaluation returned None'
            print(f"Evaluation error: {error_msg}")
            return jsonify({'error': error_msg}), 500

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error during evaluation: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
