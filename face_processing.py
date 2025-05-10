# threadfinder_webapp/face_processing.py
import face_recognition
import os
import numpy as np

# These are no longer primary config constants here, as they'll be passed as arguments.
# They can serve as internal defaults if a value isn't provided, though the app.py should ensure they are.
DEFAULT_FACE_RECOGNITION_TOLERANCE = 0.6 # Example
DEFAULT_MIN_FACE_WIDTH_PERCENTAGE = 0.5  # Example
DEFAULT_MIN_FACE_HEIGHT_PERCENTAGE = 0.5 # Example
DEFAULT_MAX_FACES = 0                  # 0 or negative means no limit

DETECTION_MODEL = "hog"
VALID_IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp')

def load_known_faces(known_faces_dir: str) -> tuple[list, list]:
    # This function remains unchanged from the previous version
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
                except Exception as e:
                    print(f"  Warning: Could not load/process reference image {image_file_path}: {e}")
    print(f"Total known face encodings loaded: {len(known_face_encodings)}")
    return known_face_encodings, known_face_names

def get_face_annotations(
    image_path: str,
    known_face_encodings: list,
    known_face_names: list,
    tolerance: float,
    min_face_width_percentage: float,
    min_face_height_percentage: float,
    max_faces_to_process: int
) -> dict: # Now returns a dictionary with annotations and messages
    """
    Processes an image to find faces, filters them, and attempts recognition.
    """
    response_data = {"error": None, "annotations": [], "message": ""}
    
    try:
        unknown_image_array = face_recognition.load_image_file(image_path)
        img_height, img_width, _ = unknown_image_array.shape
    except Exception as e:
        print(f"Error loading target image {image_path}: {e}")
        response_data["error"] = f"Failed to load image: {e}"
        return response_data

    # 1. Find all face locations
    all_face_locations = face_recognition.face_locations(unknown_image_array, model=DETECTION_MODEL)
    initial_candidates_count = len(all_face_locations)
    # print(f"Initially found {initial_candidates_count} face candidate(s).")

    # 2. Filter by size
    min_abs_width = img_width * (min_face_width_percentage / 100.0)
    min_abs_height = img_height * (min_face_height_percentage / 100.0)
    
    sized_faces_data = [] # Stores (location_tuple, area, original_index_in_all_face_locations)
    for i, loc in enumerate(all_face_locations):
        top, right, bottom, left = loc
        width = right - left
        height = bottom - top
        if width >= min_abs_width and height >= min_abs_height:
            sized_faces_data.append({'location': loc, 'area': width * height, 'original_index': i})
    
    # print(f"{len(sized_faces_data)} face(s) after size filtering.")

    # 3. If max_faces is set, prioritize larger faces
    if max_faces_to_process > 0 and len(sized_faces_data) > max_faces_to_process:
        # Sort by area in descending order (larger faces first)
        sized_faces_data.sort(key=lambda x: x['area'], reverse=True)
        final_faces_to_process_data = sized_faces_data[:max_faces_to_process]
        # print(f"Prioritizing {len(final_faces_to_process_data)} largest faces due to limit ({max_faces_to_process}).")
    else:
        final_faces_to_process_data = sized_faces_data
    
    # 4. Get encodings for the final set of faces
    # To ensure correct encodings, get all encodings first then select by original_index
    if not final_faces_to_process_data: # No faces left after filtering
        response_data["message"] = f"No faces met the size criteria from {initial_candidates_count} initial candidates."
        return response_data

    # Get encodings for ALL initially detected faces (less efficient but safer for index mapping)
    all_unknown_face_encodings = face_recognition.face_encodings(unknown_image_array, all_face_locations)

    annotations = []
    for face_data in final_faces_to_process_data:
        top, right, bottom, left = face_data['location']
        original_index = face_data['original_index']

        # Ensure we have an encoding for this face using its original index
        if original_index >= len(all_unknown_face_encodings):
            # This should ideally not happen if all_face_locations and all_unknown_face_encodings are consistent
            print(f"Warning: Encoding not found for face at original index {original_index}. Skipping.")
            continue
        
        face_encoding_to_check = all_unknown_face_encodings[original_index]
        name = "Unknown"

        if known_face_encodings:
            matches = face_recognition.compare_faces(
                known_face_encodings, 
                face_encoding_to_check, 
                tolerance=tolerance
            )
            face_distances = face_recognition.face_distance(known_face_encodings, face_encoding_to_check)
            
            if np.any(matches):
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_face_names[best_match_index]
        
        annotations.append({
            "id": f"face-{original_index}", # Use original_index for a consistent ID
            "name": name,
            "box": {
                "left": left,
                "top": top,
                "width": (right - left),
                "height": (bottom - top)
            }
        })

    response_data["annotations"] = annotations
    
    # Construct a message about processing
    msg_parts = [f"Processed {len(annotations)} face(s)."]
    if initial_candidates_count > len(sized_faces_data) :
        msg_parts.append(f"Filtered from {initial_candidates_count} initial candidates by size.")
    if max_faces_to_process > 0 and len(sized_faces_data) > len(annotations):
        msg_parts.append(f"Limited to {max_faces_to_process} largest faces.")
    response_data["message"] = " ".join(msg_parts)
    
    return response_data