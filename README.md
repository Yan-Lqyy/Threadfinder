# Threadfinder - Face Recognition Web Application

Threadfinder is a Python and Flask-based web application designed to recognize and label known individuals in uploaded photos. It features adjustable parameters for fine-tuning recognition accuracy and performance, and an interactive interface for viewing results.

## Features

*   **Web-Based Interface:** Upload photos directly through your browser.
*   **Face Detection & Recognition:** Utilizes the `face_recognition` library (built on dlib) to find and identify faces.
*   **Known Faces Database:** Easily manage known individuals by placing their photos (filename as name/identifier) in a designated directory.
*   **Dynamic Overlays:** Recognized faces are highlighted with bounding boxes and name tags directly on the image in the browser, without modifying the original image.
*   **Interactive Results:**
    *   Hover over a face box in the image to highlight the corresponding name in a sidebar list.
    *   Hover over a name in the sidebar list to highlight the corresponding face in the image.
*   **Adjustable Parameters (via UI):**
    *   **Recognition Tolerance:** Controls the strictness of face matching (lower is stricter).
    *   **Minimum Face Size:** Filters out very small faces based on a percentage of the image dimensions, improving performance and reducing misidentifications of background faces.
    *   **Max Faces to Detail:** Limits the number of faces processed, prioritizing larger faces if the limit is exceeded.
*   **Reprocess Option:** Change parameters and re-process the currently uploaded image without needing to re-upload.
*   **File Size Limit:** Accepts images up to 5MB.
*   **Loading Indicator:** Provides user feedback during image upload and processing.

## Technology Stack

*   **Backend:**
    *   **Python 3.x**
    *   **Flask:** Micro web framework for handling requests and serving the application.
    *   **face_recognition:** High-level Python API for face detection, encoding, and comparison (based on dlib).
    *   **dlib:** Toolkit containing machine learning algorithms and tools for creating complex software in C++ to solve real world problems. `face_recognition` relies heavily on dlib's pre-trained models for face detection and landmark prediction.
    *   **Pillow (PIL Fork):** Used internally by `face_recognition` for image manipulation, though not directly for drawing in this web app version.
    *   **NumPy:** For numerical operations, especially with face encodings.
*   **Frontend:**
    *   **HTML5**
    *   **CSS3:** For styling and layout, including responsive design elements.
    *   **Vanilla JavaScript (ES6+):** For dynamic UI updates, API calls (fetch), event handling, and rendering overlays.

## Python Implementation Details

### 1. `face_processing.py` (Core Logic)

This module encapsulates the face recognition pipeline:

*   **`load_known_faces(known_faces_dir)`:**
    *   Recursively scans the `known_faces_dir` and its subdirectories.
    *   For each valid image file found, it assumes the filename (sans extension, with underscores replaced by spaces) is the person's name or identifier.
    *   It loads the image using `face_recognition.load_image_file()`.
    *   Computes the 128-dimension face encoding for the first face found in each image using `face_recognition.face_encodings()`.
    *   Stores these encodings and corresponding names in memory (loaded once at application startup).
*   **`get_face_annotations(...)`:**
    *   Takes the path to an uploaded image and the loaded known face data, along with user-defined parameters (tolerance, min face size percentages, max faces).
    *   Loads the uploaded image.
    *   **Face Detection:** Finds all face locations in the image using `face_recognition.face_locations(model="hog")`. The "hog" (Histogram of Oriented Gradients) model is faster but less accurate than the "cnn" model.
    *   **Size Filtering:** Calculates the minimum required pixel width and height based on the `min_face_width_percentage` and `min_face_height_percentage` parameters and the image's dimensions. Faces smaller than these thresholds are discarded.
    *   **Max Faces Prioritization:** If `max_faces_to_process` is set and more faces remain after size filtering, it sorts the remaining faces by their bounding box area (descending) and processes only the largest `max_faces_to_process` faces.
    *   **Face Encoding:** Computes face encodings for the filtered set of faces using `face_recognition.face_encodings()`.
    *   **Face Recognition:** For each unknown face encoding:
        *   Compares it against all `known_face_encodings` using `face_recognition.compare_faces(tolerance=...)`. This returns a list of boolean matches.
        *   Calculates the Euclidean distance to all known faces using `face_recognition.face_distance()`.
        *   If any matches are found within the given `tolerance`, the known face with the smallest distance (best match) is chosen as the recognized name. Otherwise, the face is labeled "Unknown".
    *   Returns a list of annotation objects, each containing a unique ID, the recognized name, and the bounding box coordinates (`left`, `top`, `width`, `height`).

### 2. `app.py` (Flask Application)

*   **Initialization (`initialize_app()`):**
    *   Creates the `uploads/` directory if it doesn't exist.
    *   Calls `face_processing.load_known_faces()` to load the known face encodings and names into global variables. This happens once when the Flask application starts.
*   **Configuration:**
    *   `UPLOAD_FOLDER`: Specifies the directory for temporary storage of uploaded images.
    *   `KNOWN_FACES_DIR`: Specifies the directory containing reference images of known people.
    *   `MAX_CONTENT_LENGTH`: Sets the maximum allowed file size for uploads (e.g., 5MB).
*   **Routes:**
    *   **`/` (GET):** Serves the main `index.html` page using `render_template()`.
    *   **`/recognize` (POST):**
        *   Handles file uploads.
        *   Validates the file (checks extension, existence).
        *   Retrieves processing parameters (tolerance, min face size, max faces) from the form data.
        *   Saves the uploaded file to the `UPLOAD_FOLDER` with a unique filename (using `uuid`).
        *   Calls `face_processing.get_face_annotations()` with the image path and parameters.
        *   Returns a JSON response containing:
            *   `image_url`: A URL for the frontend to display the (unmodified) uploaded image.
            *   `annotations`: The list of face annotation objects.
            *   `original_filename`: The original name of the uploaded file.
            *   `message`: A status message from the processing.
            *   `error`: An error message if processing failed.
    *   **`/uploads/<filename>` (GET):** Serves uploaded images from the `UPLOAD_FOLDER` using `send_from_directory()`. This allows the `<img>` tag in the frontend to display the processed image.

## Frontend Implementation (HTML, CSS, JavaScript)

*   **`templates/index.html`:**
    *   Provides the basic page structure.
    *   Includes input fields (`<input type="file">`, sliders, number input) for image upload and parameter adjustment.
    *   Contains an `<img>` tag (`#imageDisplay`) to show the uploaded photo.
    *   An overlay `<div>` (`#overlayContainer`) is positioned directly on top of the image to hold dynamically generated bounding boxes and name tags.
    *   A sidebar `<ul>` (`#recognizedNamesList`) to display the list of recognized names.
    *   Elements for displaying status messages and loading indicators.
*   **`static/css/style.css`:**
    *   Styles all UI elements for a clean, modern, and responsive look.
    *   Defines styles for:
        *   Bounding boxes (`.bounding-box`): Border, opacity, absolute positioning.
        *   Name tags (`.name-tag`): Background, color, font, positioning relative to the box.
        *   Highlight effects (`.highlighted`): Changes appearance of boxes, tags, and list items on hover/interaction.
        *   Loading spinner and messages.
*   **`static/js/main.js`:**
    *   **Event Handling:**
        *   Listens for changes on the file input (`#imageUpload`) to trigger image processing.
        *   Listens for clicks on the "Reprocess" button.
        *   Updates displayed values for range sliders.
    *   **`processImage(file, isReprocess)`:**
        *   Handles client-side file size validation.
        *   Displays a loading indicator and disables controls.
        *   Constructs `FormData` object including the image file and current parameter values.
        *   Uses the `fetch` API to send a POST request to the `/recognize` backend endpoint.
        *   Handles the JSON response from the backend.
        *   Updates the `<img>` source and calls `renderAnnotationsAndNames()`.
        *   Manages UI state for success, errors, and loading.
    *   **`renderAnnotationsAndNames(annotations)`:**
        *   Clears previous overlays and name list items.
        *   Calculates scaling factors (`scaleX`, `scaleY`) by comparing the image's natural (original) dimensions with its displayed dimensions in the browser. This is crucial for accurately positioning overlays on a responsive image.
        *   For each annotation received from the backend:
            *   Dynamically creates `<div>` elements for the bounding box and the name tag.
            *   Applies scaled coordinates and dimensions to these elements using CSS `style` properties.
            *   Appends them to `#overlayContainer`.
            *   Creates an `<li>` element for the name and appends it to `#recognizedNamesList`.
            *   Attaches `mouseenter` and `mouseleave` event listeners to boxes and list items to trigger `highlightFace()`.
    *   **`highlightFace(faceId, isHighlighted)`:**
        *   Adds or removes a `.highlighted` CSS class to the corresponding face box, (optional) name tag, and list item based on the provided `faceId`.
    *   **Error Handling:** Displays error messages from the server or client-side issues.
    *   **UI State Management:** Shows/hides loading indicators, enables/disables controls appropriately.

## Special Case: dlib Installation (and `face_recognition`)

The `face_recognition` library, and by extension `dlib`, can sometimes be challenging to install due to its C++ dependencies and the need for a C++ compiler and CMake.

**Common Requirements:**

*   **C++ Compiler:** Like GCC (on Linux) or MSVC (on Windows, via Visual Studio Build Tools).
*   **CMake:** A cross-platform build system generator.
*   **Boost (sometimes):** `dlib` might require Boost Python libraries.
*   **Python Development Headers:** `python3-dev` or `python3-devel` on Linux.

**Installation Process & Potential Issues:**

1.  **Recommended First Step (Using Wheels):**
    ```bash
    pip install face_recognition
    ```
    This command will attempt to install `dlib` first. For common Python versions and operating systems, pre-compiled binary wheels for `dlib` are often available on PyPI, making installation straightforward.

2.  **If Wheels Fail (Source Compilation):**
    If a pre-compiled wheel isn't found for your specific environment, `pip` will try to build `dlib` from source. This is where issues often arise.
    *   **Linux:**
        *   Install prerequisites: `sudo apt-get update && sudo apt-get install build-essential cmake libopenblas-dev liblapack-dev libx11-dev python3-dev` (Debian/Ubuntu). For Fedora/CentOS, use `dnf` or `yum` and look for equivalent packages (e.g., `cmake`, `gcc-c++`, `python3-devel`).
        *   Then try `pip install dlib` followed by `pip install face_recognition`.
    *   **macOS:**
        *   Install Xcode Command Line Tools: `xcode-select --install`.
        *   Install CMake: `brew install cmake`.
        *   Then try `pip install dlib` and `pip install face_recognition`.
    *   **Windows:**
        *   **Crucial:** Install "Build Tools for Visual Studio" (making sure the C++ build tools component is selected during installation).
        *   Install CMake and add it to your system PATH.
        *   Then try `pip install dlib` and `pip install face_recognition` from a command prompt that has the Visual Studio build environment activated (e.g., "Developer Command Prompt for VS").
        *   Sometimes, installing `dlib` via `conda` (if you use Anaconda/Miniconda) can be easier on Windows: `conda install -c conda-forge dlib` then `pip install face_recognition`.

3.  **CMake Errors:**
    *   "CMake must be installed..." : Ensure CMake is installed and in your system's PATH.
    *   Errors during the CMake build process often point to missing C++ compiler, libraries, or Python development headers. The error messages can be long and cryptic, but looking near the top for messages like "Could not find [library]" or compiler errors can give clues.

4.  **GPU Support (for CNN model):**
    If you want to use the more accurate `cnn` face detection model with GPU acceleration, `dlib` must be compiled with CUDA support. This typically involves:
    *   Having an NVIDIA GPU with CUDA toolkit and cuDNN installed.
    *   Building `dlib` from source with specific CMake flags pointing to your CUDA installation (e.g., `python setup.py install --yes DLIB_USE_CUDA`). This is an advanced setup.

**Troubleshooting Tips:**

*   **Read Error Messages Carefully:** They often contain hints about missing dependencies.
*   **Virtual Environments:** Always use Python virtual environments (`venv`, `conda env`) to isolate project dependencies and avoid conflicts.
*   **Check `face_recognition` and `dlib` Documentation:** The official GitHub repositories for these libraries often have detailed installation instructions and troubleshooting guides.
*   **Search Online:** Copy-paste specific error messages into a search engine. Many developers have encountered similar issues.

## Running the Application

1.  **Clone the Repository (Not covered here, as per request).**
2.  **Install Dependencies:**
    ```bash
    pip install Flask face_recognition Pillow numpy
    ```
    *(Ensure dlib installs correctly, see "Special Case" above if issues arise).*
3.  **Create `known_faces` Directory:**
    Inside the project's root directory (`threadfinder_webapp/`), create a folder named `known_faces/`.
    Populate this folder with images of people you want the application to recognize. The filename (without extension, underscores become spaces) will be used as the person's name. You can also use subdirectories within `known_faces/`.
4.  **Run the Flask Application:**
    Navigate to the `threadfinder_webapp/` directory in your terminal and execute:
    ```bash
    python app.py
    ```
5.  **Access in Browser:**
    Open your web browser and go to `http://127.0.0.1:5000/` (or `http://YOUR_SERVER_IP:5000/` if `host='0.0.0.0'` is used and you're accessing from another device on the network).

## Future Enhancements

*   **Persistent Storage for Known Faces:** For larger databases of known faces, load encodings from a database (e.g., SQLite, PostgreSQL with pgvector) or pre-computed files instead of re-processing images on every app start.
*   **ANN Indexing:** For very large known face datasets, integrate Approximate Nearest Neighbor (ANN) search libraries (like Faiss or Annoy) for faster comparisons.
*   **Asynchronous Processing:** For long-running face recognition tasks (especially with large images or the CNN model), use a task queue (like Celery) to process images in the background without blocking web requests.
*   **User Accounts & Management of Known Faces:** Allow users to manage their own sets of known faces through the web interface.
*   **More Robust Error Handling and Logging.**
*   **Option to use the CNN model for face detection (with clear indication of performance impact).**

---
