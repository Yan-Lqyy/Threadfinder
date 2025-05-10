# threadfinder_webapp/app.py
from flask import Flask, request, jsonify, render_template, send_from_directory
import os
import uuid # For generating unique filenames
from werkzeug.utils import secure_filename # For securing filenames
import face_processing # Our custom module

# --- Flask App Setup ---
app = Flask(__name__)

# --- Configuration ---
# Get the absolute path of the directory where this script is located
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Configure upload folder relative to the script's location
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
KNOWN_FACES_DIR = r"SOME DIR HERE" # Directory containing known faces
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# --- Global Variables for Known Faces (Loaded at Startup) ---
# These will be populated when the application starts
KNOWN_FACE_ENCODINGS = []
KNOWN_FACE_NAMES = []

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Application Initialization ---
def initialize_app():
    global KNOWN_FACE_ENCODINGS, KNOWN_FACE_NAMES
    
    # Create upload folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
        print(f"Created upload folder: {UPLOAD_FOLDER}")

    # Load known faces
    print("Initializing Threadfinder: Loading known faces...")
    KNOWN_FACE_ENCODINGS, KNOWN_FACE_NAMES = face_processing.load_known_faces(KNOWN_FACES_DIR)
    if not KNOWN_FACE_ENCODINGS:
        print("WARNING: No known faces were loaded. Recognition will not work effectively.")
    else:
        print(f"Successfully loaded {len(KNOWN_FACE_ENCODINGS)} known face(s).")

# --- Routes ---
@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')

@app.route('/recognize', methods=['POST'])
def recognize_faces_api():
    """
    API endpoint to receive an image, process it for face recognition,
    and return annotations.
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part in the request"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected for uploading"}), 400

    if file and allowed_file(file.filename):
        # Secure the filename and make it unique
        original_filename = secure_filename(file.filename)
        extension = original_filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4()}.{extension}"
        
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        try:
            file.save(image_path)
        except Exception as e:
            print(f"Error saving file: {e}")
            return jsonify({"error": "Failed to save uploaded file"}), 500

        # Process the image to get face annotations
        annotations = face_processing.get_face_annotations(
            image_path,
            KNOWN_FACE_ENCODINGS,
            KNOWN_FACE_NAMES
        )
        
        # Provide a URL to the uploaded image so the frontend can display it
        image_url = f"/uploads/{unique_filename}" 

        return jsonify({
            "image_url": image_url,
            "annotations": annotations,
            "original_filename": original_filename # For display purposes
        })
    else:
        return jsonify({"error": "Invalid file type"}), 400

@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    """Serves files from the UPLOAD_FOLDER."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- Main Execution ---
if __name__ == '__main__':
    initialize_app() # Load known faces and setup folders
    app.run(debug=False, host='0.0.0.0') # host='0.0.0.0' makes it accessible on your network