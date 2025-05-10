// threadfinder_webapp/static/js/main.js
document.addEventListener('DOMContentLoaded', () => {
    const imageUpload = document.getElementById('imageUpload');
    const imageDisplay = document.getElementById('imageDisplay');
    const overlayContainer = document.getElementById('overlayContainer');
    const resultsDisplay = document.getElementById('resultsDisplay');
    const imageNameDisplay = document.getElementById('imageName');
    const processingStatus = document.getElementById('processingStatus'); // Changed ID
    const recognizedNamesList = document.getElementById('recognizedNamesList');
    const namesPanelStatus = document.getElementById('namesPanelStatus');

    imageUpload.addEventListener('change', async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        resultsDisplay.style.display = 'flex'; // Changed to flex
        imageNameDisplay.textContent = file.name; // Show original name initially
        processingStatus.textContent = 'Uploading and processing... Please wait.';
        recognizedNamesList.innerHTML = ''; // Clear previous names
        overlayContainer.innerHTML = ''; // Clear previous overlays
        namesPanelStatus.textContent = '';
        imageDisplay.src = '#'; // Clear previous image

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/recognize', { method: 'POST', body: formData });
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({ error: "Unknown server error" }));
                throw new Error(`Server error: ${response.status} - ${errorData.error || 'Failed to get error details'}`);
            }
            const data = await response.json();

            if (data.error) {
                processingStatus.textContent = `Error: ${data.error}`;
                return;
            }

            imageNameDisplay.textContent = data.original_filename || file.name;
            imageDisplay.src = data.image_url;

            imageDisplay.onload = () => {
                renderAnnotationsAndNames(data.annotations);
                processingStatus.textContent = `Processed ${data.annotations.length} face(s) after filtering.`;
            };
            if (imageDisplay.complete) imageDisplay.onload();

        } catch (error) {
            console.error('Error:', error);
            processingStatus.textContent = `Client error: ${error.message}`;
        }
    });

    function renderAnnotationsAndNames(annotations) {
        overlayContainer.innerHTML = '';
        recognizedNamesList.innerHTML = '';

        if (annotations.length === 0) {
            namesPanelStatus.textContent = "No faces recognized or all were too small.";
            return;
        }

        const naturalWidth = imageDisplay.naturalWidth;
        const naturalHeight = imageDisplay.naturalHeight;
        const displayedWidth = imageDisplay.offsetWidth;
        const displayedHeight = imageDisplay.offsetHeight;

        if (naturalWidth === 0 || naturalHeight === 0) {
            console.error("Image natural dimensions are zero.");
            namesPanelStatus.textContent = "Error: Could not get image dimensions.";
            return;
        }

        const scaleX = displayedWidth / naturalWidth;
        const scaleY = displayedHeight / naturalHeight;

        annotations.forEach(ann => {
            const { id, name, box } = ann; // Destructure for easier access
            const dispLeft = box.left * scaleX;
            const dispTop = box.top * scaleY;
            const dispWidth = box.width * scaleX;
            const dispHeight = box.height * scaleY;

            // Create Bounding Box
            const boxDiv = document.createElement('div');
            boxDiv.className = 'bounding-box';
            boxDiv.id = `box-${id}`; // Use the ID from backend
            boxDiv.style.left = `${dispLeft}px`;
            boxDiv.style.top = `${dispTop}px`;
            boxDiv.style.width = `${dispWidth}px`;
            boxDiv.style.height = `${dispHeight}px`;
            
            // Create Name Tag (inside box for better positioning context with transform)
            const nameTagDiv = document.createElement('div');
            nameTagDiv.className = 'name-tag';
            nameTagDiv.id = `nametag-${id}`;
            nameTagDiv.textContent = name;
            // CSS will position this above the box based on .bounding-box context
            boxDiv.appendChild(nameTagDiv); 
            overlayContainer.appendChild(boxDiv);

            // Create List Item for Name Panel
            const listItem = document.createElement('li');
            listItem.textContent = name === "Unknown" ? `Unknown Face #${annotations.indexOf(ann)+1}` : name;
            listItem.dataset.faceId = id; // Store face ID for linking
            listItem.id = `listitem-${id}`;
            recognizedNamesList.appendChild(listItem);

            // Add interactivity
            [boxDiv, listItem].forEach(el => {
                el.addEventListener('mouseenter', () => highlightFace(id, true));
                el.addEventListener('mouseleave', () => highlightFace(id, false));
            });
        });
        namesPanelStatus.textContent = `${annotations.length} recognized.`;
    }

    function highlightFace(faceId, isHighlighted) {
        const boxElement = document.getElementById(`box-${faceId}`);
        const nameTagElement = document.getElementById(`nametag-${faceId}`); // Corrected name tag selection
        const listItemElement = document.getElementById(`listitem-${faceId}`);

        if (boxElement) boxElement.classList.toggle('highlighted', isHighlighted);
        if (nameTagElement) nameTagElement.classList.toggle('highlighted', isHighlighted); // Corrected
        if (listItemElement) listItemElement.classList.toggle('highlighted', isHighlighted);
    }
});