// threadfinder_webapp/static/js/main.js
document.addEventListener('DOMContentLoaded', () => {
    // UI Elements
    const imageUpload = document.getElementById('imageUpload');
    const imageDisplay = document.getElementById('imageDisplay');
    const overlayContainer = document.getElementById('overlayContainer');
    const resultsDisplay = document.getElementById('resultsDisplay');
    const imageNameDisplay = document.getElementById('imageName');
    const processingIndicator = document.getElementById('processingIndicator');
    const processingStatusText = document.getElementById('processingStatusText');
    const recognizedNamesList = document.getElementById('recognizedNamesList');
    const namesPanelStatus = document.getElementById('namesPanelStatus');
    const resultStats = document.getElementById('resultStats');
    const reprocessButton = document.getElementById('reprocessButton');

    // Parameter Inputs & Displays
    const toleranceInput = document.getElementById('tolerance');
    const toleranceValueDisplay = document.getElementById('toleranceValue');
    const minFaceWidthPercentageInput = document.getElementById('minFaceWidthPercentage');
    const minFaceWidthPercentageValueDisplay = document.getElementById('minFaceWidthPercentageValue');
    const minFaceHeightPercentageInput = document.getElementById('minFaceHeightPercentage');
    const minFaceHeightPercentageValueDisplay = document.getElementById('minFaceHeightPercentageValue');
    const maxFacesInput = document.getElementById('maxFaces');

    const controlElements = [
        imageUpload, toleranceInput, minFaceWidthPercentageInput, 
        minFaceHeightPercentageInput, maxFacesInput, reprocessButton
    ];

    const MAX_FILE_SIZE_MB = 5;
    const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

    let currentFile = null; // Store the current file for reprocessing

    // Update display values for range sliders
    function setupRangeSlider(inputElement, displayElement) {
        displayElement.textContent = inputElement.value;
        inputElement.addEventListener('input', () => {
            displayElement.textContent = inputElement.value;
        });
    }
    setupRangeSlider(toleranceInput, toleranceValueDisplay);
    setupRangeSlider(minFaceWidthPercentageInput, minFaceWidthPercentageValueDisplay);
    setupRangeSlider(minFaceHeightPercentageInput, minFaceHeightPercentageValueDisplay);

    imageUpload.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (!file) {
            currentFile = null;
            reprocessButton.style.display = 'none';
            return;
        }
        currentFile = file;
        processImage(file, false); // false indicates it's a new upload
    });

    reprocessButton.addEventListener('click', () => {
        if (currentFile) {
            processImage(currentFile, true); // true indicates it's a reprocess
        } else {
            alert("Please choose an image first.");
        }
    });

    async function processImage(file, isReprocess) {
        if (!isReprocess) { // Only check size on initial new upload
            if (file.size > MAX_FILE_SIZE_BYTES) {
                alert(`File is too large (${(file.size / (1024*1024)).toFixed(2)}MB). Maximum size is ${MAX_FILE_SIZE_MB}MB.`);
                imageUpload.value = ''; // Clear the input
                currentFile = null;
                reprocessButton.style.display = 'none';
                return;
            }
        }

        // UI updates for loading state
        resultsDisplay.style.display = 'none';
        processingIndicator.style.display = 'flex';
        processingStatusText.textContent = isReprocess ? 'Re-processing with new settings...' : 'Uploading and processing...';
        toggleControls(false); // Disable controls

        const formData = new FormData();
        formData.append('file', file);
        formData.append('tolerance', toleranceInput.value);
        formData.append('minFaceWidthPercentage', minFaceWidthPercentageInput.value);
        formData.append('minFaceHeightPercentage', minFaceHeightPercentageInput.value);
        formData.append('maxFaces', maxFacesInput.value);

        try {
            const response = await fetch('/recognize', { method: 'POST', body: formData });
            
            // Always hide indicator and re-enable controls after fetch, regardless of outcome
            processingIndicator.style.display = 'none';
            toggleControls(true);

            const data = await response.json(); // Try to parse JSON regardless of status for error messages

            if (!response.ok) {
                let errorMsg = `Error ${response.status}: `;
                if (response.status === 413) {
                    errorMsg += `File too large (max ${MAX_FILE_SIZE_MB}MB).`;
                } else {
                    errorMsg += data.error || "An unknown server error occurred.";
                }
                displayErrorState(errorMsg, file.name);
                return;
            }
            
            // Handle application-level errors returned in a successful HTTP response
            if (data.error) {
                displayErrorState(`Processing Error: ${data.error}`, data.original_filename || file.name, data.image_url);
                return;
            }

            // Success
            resultsDisplay.style.display = 'flex';
            reprocessButton.style.display = 'inline-block';
            imageNameDisplay.textContent = data.original_filename || file.name;
            imageDisplay.src = data.image_url; // This will trigger onload

            imageDisplay.onload = () => {
                renderAnnotationsAndNames(data.annotations);
                resultStats.textContent = data.message || `Found ${data.annotations.length} face(s).`;
                namesPanelStatus.textContent = data.annotations.length > 0 ? "" : "No faces found meeting criteria.";
                namesPanelStatus.classList.remove('error');
            };
            if (imageDisplay.complete) imageDisplay.onload(); // If already loaded from cache

        } catch (error) { // Network errors or issues with fetch itself
            console.error('Client-side fetch error:', error);
            processingIndicator.style.display = 'none';
            toggleControls(true);
            displayErrorState(`Client Error: ${error.message}. Check network or console.`, file.name);
        }
    }

    function displayErrorState(errorMessage, fileName, imageUrl = null) {
        resultsDisplay.style.display = 'flex'; // Show results area to display error message
        imageNameDisplay.textContent = `Error with: ${fileName}`;
        namesPanelStatus.textContent = errorMessage;
        namesPanelStatus.classList.add('error'); // Style error message
        resultStats.textContent = "";
        overlayContainer.innerHTML = '';
        recognizedNamesList.innerHTML = '';
        if (imageUrl) {
            imageDisplay.src = imageUrl; // Show image if available, even on error
        } else {
            imageDisplay.src = '#'; // Clear image
        }
        reprocessButton.style.display = currentFile ? 'inline-block' : 'none'; // Allow reprocess if file exists
    }
    
    function toggleControls(enable) {
        controlElements.forEach(el => el.disabled = !enable);
        if (enable && !currentFile) { // If enabling but no file, reprocess stays hidden/disabled
             reprocessButton.style.display = 'none';
        } else if (enable && currentFile) {
            reprocessButton.style.display = 'inline-block';
            reprocessButton.disabled = false;
        }
    }

    function renderAnnotationsAndNames(annotations) {
        overlayContainer.innerHTML = '';
        recognizedNamesList.innerHTML = '';

        if (!annotations || annotations.length === 0) {
            // Message handled by caller (resultStats or namesPanelStatus)
            return;
        }

        const naturalWidth = imageDisplay.naturalWidth;
        const naturalHeight = imageDisplay.naturalHeight;
        const displayedWidth = imageDisplay.offsetWidth;
        const displayedHeight = imageDisplay.offsetHeight;

        if (naturalWidth === 0 || naturalHeight === 0) {
            namesPanelStatus.textContent = "Error: Could not get image dimensions for scaling annotations.";
            namesPanelStatus.classList.add('error');
            return;
        }

        const scaleX = displayedWidth / naturalWidth;
        const scaleY = displayedHeight / naturalHeight;

        annotations.forEach(ann => {
            const { id, name, box } = ann;
            const dispLeft = box.left * scaleX;
            const dispTop = box.top * scaleY;
            const dispWidth = box.width * scaleX;
            const dispHeight = box.height * scaleY;

            const boxDiv = document.createElement('div');
            boxDiv.className = 'bounding-box';
            boxDiv.id = `box-${id}`;
            boxDiv.style.left = `${dispLeft}px`;
            boxDiv.style.top = `${dispTop}px`;
            boxDiv.style.width = `${dispWidth}px`;
            boxDiv.style.height = `${dispHeight}px`;
            
            const nameTagDiv = document.createElement('div');
            nameTagDiv.className = 'name-tag';
            nameTagDiv.id = `nametag-${id}`;
            nameTagDiv.textContent = name;
            boxDiv.appendChild(nameTagDiv); 
            overlayContainer.appendChild(boxDiv);

            const listItem = document.createElement('li');
            // For "Unknown", show a part of its unique ID to differentiate if multiple unknowns
            const displayName = name === "Unknown" ? `Unknown (${id.split('-').pop()})` : name;
            listItem.textContent = displayName;
            listItem.dataset.faceId = id;
            listItem.id = `listitem-${id}`;
            recognizedNamesList.appendChild(listItem);

            [boxDiv, listItem].forEach(el => {
                el.addEventListener('mouseenter', () => highlightFace(id, true));
                el.addEventListener('mouseleave', () => highlightFace(id, false));
            });
        });
    }

    function highlightFace(faceId, isHighlighted) {
        const boxElement = document.getElementById(`box-${faceId}`);
        // Name tag is child of box, its highlighting can be managed by CSS if box is highlighted
        // For explicit control or if structure changes:
        // const nameTagElement = document.getElementById(`nametag-${faceId}`); 
        const listItemElement = document.getElementById(`listitem-${faceId}`);

        if (boxElement) boxElement.classList.toggle('highlighted', isHighlighted);
        // if (nameTagElement) nameTagElement.classList.toggle('highlighted', isHighlighted);
        if (listItemElement) listItemElement.classList.toggle('highlighted', isHighlighted);
    }
});