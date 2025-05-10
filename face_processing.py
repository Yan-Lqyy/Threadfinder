# threadfinder_webapp/face_processing.py
import face_recognition
import os
import numpy as np

# --- Configuration ---
# These can be adjusted as needed
FACE_RECOGNITION_TOLERANCE = 0.55 # As adjusted in the previous step
DETECTION_MODEL = "hog" # "hog" is faster, "cnn" is more accurate (requires dlib compiled with CUDA for GPU)
VALID_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')

# --- New Configuration for Minimum Face Size by Percentage ---
# Ignore faces if their width is less than this percentage of image width
MIN_FACE_WIDTH_PERCENTAGE = 10
# Ignore faces if their height is less than this percentage of image height
MIN_FACE_HEIGHT_PERCENTAGE = 10

# --- Helper Functions ---

def load_known_faces(known_faces_dir: str) -> tuple[list, list]:
    """
    Loads known faces by traversing the known_faces_dir and its subdirectories.
    Every image file found is treated as a reference photo for one person.
    The person's name is derived from the filename (without extension),
    with underscores replaced by spaces.

    Args:
        known_faces_dir: Path to the root directory containing known faces.

    Returns:
        A tuple containing:
            - known_face_encodings: A list of 128-dimension face encodings.
            - known_face_names: A list of names corresponding to the encodings.
    """
    known_face_encodings = []
    known_face_names = []

    print(f"Loading known faces from '{known_faces_dir}'...")
    if not os.path.exists(known_faces_dir) or not os.path.isdir(known_faces_dir):
         print(f"Warning: Known faces path '{known_faces_dir}' not found or is not a directory.")
         return known_face_encodings, known_face_names

    for dirpath, _, filenames in os.walk(known_faces_dir):
        for filename in filenames:
            if filename.lower().endswith(VALID_IMAGE_EXTENSIONS):
                image_file_path = os.path.join(dirpath, filename)
                person_name = os.path.splitext(filename)[0].replace("_", " ")

                try:
                    image_array = face_recognition.load_image_file(image_file_path)
                    encodings = face_recognition.face_encodings(image_array)

                    if encodings:
                        known_face_encodings.append(encodings[0])
                        known_face_names.append(person_name)
                        # print(f"  - Loaded '{person_name}' from {filename}") # Verbose
                    else:
                        # print(f"  Warning: No face found in reference image {image_file_path} ('{person_name}') - skipping.")
                        pass # Keep output cleaner if many reference images have no faces

                except Exception as e:
                    print(f"  Warning: Could not load/process reference image {image_file_path} ('{person_name}'): {e}")
    
    print(f"Total known face encodings loaded: {len(known_face_encodings)}")
    return known_face_encodings, known_face_names

def get_face_annotations(
    image_path: str,
    known_face_encodings: list,
    known_face_names: list
) -> list:
    """
    Processes an image to find faces and attempts to recognize them against known faces.
    Filters out faces smaller than a specified percentage of the image dimensions.
    Returns a list of annotations (name and bounding box) for each detected face.

    Args:
        image_path: Path to the image to process.
        known_face_encodings: List of known face encodings.
        known_face_names: List of names for known faces.

    Returns:
        A list of dictionaries, where each dictionary contains:
        {
            "id": str,  // Unique identifier for the face in this image
            "name": str,  // Recognized name or "Unknown"
            "box": {"left": int, "top": int, "width": int, "height": int} // Bounding box
        }
    """
    annotations = []
    try:
        unknown_image_array = face_recognition.load_image_file(image_path)
        img_height, img_width, _ = unknown_image_array.shape # Get image dimensions (height, width, channels)
    except Exception as e:
        print(f"Error loading target image {image_path}: {e}")
        return annotations # Return empty list on error

    face_locations = face_recognition.face_locations(unknown_image_array, model=DETECTION_MODEL)
    unknown_face_encodings = face_recognition.face_encodings(unknown_image_array, face_locations)

    print(f"Initially found {len(face_locations)} face(s) in the uploaded image.")

    # Calculate minimum required dimensions based on percentage
    min_width_pixels = img_width * (MIN_FACE_WIDTH_PERCENTAGE / 100.0)
    min_height_pixels = img_height * (MIN_FACE_HEIGHT_PERCENTAGE / 100.0)
    
    processed_face_count = 0 # Counter for faces after filtering

    for i, (top, right, bottom, left) in enumerate(face_locations):
        width = right - left
        height = bottom - top

        # --- Filter for small faces based on percentage ---
        # Ignore the face if its width is too small OR its height is too small
        if width < min_width_pixels or height < min_height_pixels:
            # print(f"  - Ignoring small face (width {width}px, height {height}px): min_width={min_width_pixels:.2f}px, min_height={min_height_pixels:.2f}px") # Optional: for debugging
            continue 
        # --- End filter ---
        
        processed_face_count += 1


        face_encoding_to_check = unknown_face_encodings[i]
        name = "Unknown"

        if known_face_encodings:
            matches = face_recognition.compare_faces(
                known_face_encodings, 
                face_encoding_to_check, 
                tolerance=FACE_RECOGNITION_TOLERANCE
            )
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding_to_check)
            
            if np.any(matches):
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]
        
        annotations.append({
            "id": f"face-{i}", # Unique ID for this face in this image
            "name": name,
            "box": {
                "left": left,
                "top": top,
                "width": width,
                "height": height
            }
        })
    print(f"Processing {processed_face_count} face(s) after filtering by size ({MIN_FACE_WIDTH_PERCENTAGE}% width, {MIN_FACE_HEIGHT_PERCENTAGE}% height).")
    return annotations