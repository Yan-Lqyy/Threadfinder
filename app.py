# threadfinder_webapp/app.py
from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import uuid
from werkzeug.utils import secure_filename
import face_processing # Our custom module

app = Flask(__name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
KNOWN_FACES_DIR = r"SOME DIR HERE" # Directory where known faces are stored
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max upload size

KNOWN_FACE_ENCODINGS = []
KNOWN_FACE_NAMES = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def initialize_app():
    global KNOWN_FACE_ENCODINGS, KNOWN_FACE_NAMES
    if not os.path.exists(UPLOAD_FOLDER):
        try:
            os.makedirs(UPLOAD_FOLDER)
            print(f"Created upload folder: {UPLOAD_FOLDER}")
        except OSError as e:
            print(f"Error creating upload folder {UPLOAD_FOLDER}: {e}")
            # Depending on severity, you might want to exit or handle differently
            
    print("Initializing Threadfinder: Loading known faces...")
    KNOWN_FACE_ENCODINGS, KNOWN_FACE_NAMES = face_processing.load_known_faces(KNOWN_FACES_DIR)
    if not KNOWN_FACE_ENCODINGS:
        print("WARNING: No known faces were loaded. Recognition may not be effective.")
    else:
        print(f"Successfully loaded {len(KNOWN_FACE_ENCODINGS)} known face(s).")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recognize', methods=['POST'])
def recognize_faces_api():
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400

    if file and allowed_file(file.filename):
        # Get parameters from form data, with defaults from face_processing if not provided
        try:
            tolerance = float(request.form.get('tolerance', face_processing.DEFAULT_FACE_RECOGNITION_TOLERANCE))
            min_width_perc = float(request.form.get('minFaceWidthPercentage', face_processing.DEFAULT_MIN_FACE_WIDTH_PERCENTAGE))
            min_height_perc = float(request.form.get('minFaceHeightPercentage', face_processing.DEFAULT_MIN_FACE_HEIGHT_PERCENTAGE))
            max_faces = int(request.form.get('maxFaces', face_processing.DEFAULT_MAX_FACES))
            if max_faces < 0: max_faces = 0 # Ensure non-negative, 0 for no limit
        except ValueError:
            return jsonify({"error": "Invalid parameter value type provided."}), 400

        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else ''
        unique_filename = f"{uuid.uuid4()}.{extension}" if extension else str(uuid.uuid4())
        
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            file.save(image_path)
        except Exception as e:
            print(f"Error saving file: {e}")
            return jsonify({"error": "Failed to save uploaded file."}), 500

        # Call the processing function
        result_data = face_processing.get_face_annotations(
            image_path,
            KNOWN_FACE_ENCODINGS,
            KNOWN_FACE_NAMES,
            tolerance=tolerance,
            min_face_width_percentage=min_width_perc,
            min_face_height_percentage=min_height_perc,
            max_faces_to_process=max_faces
        )
        
        image_url = f"/uploads/{unique_filename}"
        
        # Construct the final JSON response
        response_payload = {
            "image_url": image_url,
            "annotations": result_data.get("annotations", []),
            "original_filename": original_filename,
            "message": result_data.get("message", "Processing complete.")
        }
        if result_data.get("error"):
            response_payload["error"] = result_data["error"]
            # Decide on HTTP status code based on error, e.g., 500 for server-side processing issues
            return jsonify(response_payload), 500 if "Failed to load" in result_data["error"] else 400 
            
        return jsonify(response_payload)
    else:
        return jsonify({"error": "Invalid file type or no file provided."}), 400

@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    initialize_app()
    app.run(debug=False, host='0.0.0.0') # debug=False recommended for stable init