// Canvas setup
let canvas, ctx, isDrawing = false, brushSize = 15;

// Initialize canvas when DOM is loaded
document.addEventListener('DOMContentLoaded', function () {
    initializeCanvas();
});

function initializeCanvas() {
    canvas = document.getElementById('drawingCanvas');
    if (!canvas) {
        console.error('Canvas element not found!');
        return;
    }

    ctx = canvas.getContext('2d');

    // Set canvas background to black
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Set drawing style
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = brushSize;

    // Brush size control
    const brushSizeSlider = document.getElementById('brushSize');
    const brushSizeValue = document.getElementById('brushSizeValue');

    if (brushSizeSlider && brushSizeValue) {
        brushSizeSlider.addEventListener('input', function () {
            brushSize = this.value;
            brushSizeValue.textContent = this.value;
            ctx.lineWidth = brushSize;
        });
    }

    // Add event listeners for drawing
    setupDrawingEvents();


}

function setupDrawingEvents() {
    // Mouse events
    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseout', stopDrawing);

    // Touch events for mobile
    canvas.addEventListener('touchstart', handleTouch);
    canvas.addEventListener('touchmove', handleTouch);
    canvas.addEventListener('touchend', stopDrawing);
}



function startDrawing(e) {
    if (!canvas || !ctx) {
        console.error('Canvas not initialized!');
        return;
    }

    isDrawing = true;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;



    // Set up drawing style
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = brushSize;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    // Start new path
    ctx.beginPath();
    ctx.moveTo(x, y);
}

function draw(e) {
    if (!isDrawing || !canvas || !ctx) return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    // Continue the line
    ctx.lineTo(x, y);
    ctx.stroke();
}

function stopDrawing() {
    isDrawing = false;
}

function handleTouch(e) {
    e.preventDefault();
    const touch = e.touches[0];
    const mouseEvent = new MouseEvent(e.type === 'touchstart' ? 'mousedown' :
        e.type === 'touchmove' ? 'mousemove' : 'mouseup', {
        clientX: touch.clientX,
        clientY: touch.clientY
    });
    canvas.dispatchEvent(mouseEvent);
}

function clearCanvas() {
    if (!canvas || !ctx) {
        console.error('Canvas not initialized!');
        return;
    }

    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Reset drawing style
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.lineWidth = brushSize;

    // Clear results
    document.getElementById('results').innerHTML = `
        <div class="tips">
            <h3>💡 Drawing Tips:</h3>
            <ul>
                <li>Draw with white color on black background</li>
                <li>Make bold, clear strokes</li>
                <li>Center your digit in the canvas</li>
                <li>Use appropriate brush size (10-20)</li>
                <li>Draw digits similar to handwriting</li>
            </ul>
        </div>
    `;
}

function canvasToBase64() {
    return canvas.toDataURL('image/png');
}

async function classifyDigit() {
    // Check if something is drawn - look for white pixels (drawing color)
    const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const pixels = imageData.data;
    let hasDrawing = false;
    let whitePixelCount = 0;

    // Since we draw white on black, look for pixels that are not black
    for (let i = 0; i < pixels.length; i += 4) {
        // Check if any RGB component is significantly above 0 (not pure black)
        if (pixels[i] > 50 || pixels[i + 1] > 50 || pixels[i + 2] > 50) {
            whitePixelCount++;
            if (whitePixelCount > 50) { // Need sufficient pixels for a digit
                hasDrawing = true;
                break;
            }
        }
    }

    if (!hasDrawing) {
        showError('Please draw a digit first! Make sure to draw bold, clear strokes that fill some space.');
        return;
    }

    // Show loading
    showLoading();

    try {
        // Get image data
        const imageDataBase64 = canvasToBase64();

        // Send to API
        const response = await fetch('/predict', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                image_data: imageDataBase64
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();

        if (result.error) {
            showError(result.error);
        } else {
            showResults(result);
        }

    } catch (error) {
        showError('Failed to classify digit. Please try again.');
        console.error('Error:', error);
    }
}

function showLoading() {
    document.getElementById('results').innerHTML = `
        <div class="loading">
            <h3>🤖 Classifying your drawing...</h3>
            <p>Please wait while AI analyzes your digit.</p>
        </div>
    `;
}

function showError(message) {
    document.getElementById('results').innerHTML = `
        <div class="error">
            <h3>❌ Error</h3>
            <p>${message}</p>
        </div>
        <div class="tips">
            <h3>💡 Try Again:</h3>
            <ul>
                <li>Make sure you've drawn a digit</li>
                <li>Use bold, clear strokes</li>
                <li>Check your internet connection</li>
            </ul>
        </div>
    `;
}

function showResults(result) {
    const { predicted_digit, confidence, probabilities } = result;

    // Determine confidence level
    let confidenceClass = 'low-confidence';
    let confidenceText = 'Low Confidence';

    if (confidence > 0.8) {
        confidenceClass = 'high-confidence';
        confidenceText = '🟢 High Confidence';
    } else if (confidence > 0.5) {
        confidenceClass = 'medium-confidence';
        confidenceText = '🟡 Medium Confidence';
    } else {
        confidenceText = '🔴 Low Confidence';
    }

    // Create probability bars
    let probabilityBars = '';
    for (let i = 0; i < 10; i++) {
        const prob = probabilities[i.toString()] || 0;
        const percentage = (prob * 100).toFixed(1);
        const isHighest = i === predicted_digit;

        probabilityBars += `
            <div class="prob-bar">
                <div class="prob-label">Digit ${i}:</div>
                <div class="prob-visual">
                    <div class="prob-fill" style="width: ${percentage}%; ${isHighest ? 'background: linear-gradient(90deg, #ff6b6b, #ee5a24);' : ''}"></div>
                </div>
                <div class="prob-value">${percentage}%</div>
            </div>
        `;
    }

    document.getElementById('results').innerHTML = `
        <div class="prediction-result">
            <div class="predicted-digit">${predicted_digit}</div>
            <div class="confidence">Confidence: ${(confidence * 100).toFixed(1)}%</div>
            <div class="confidence-indicator ${confidenceClass}">${confidenceText}</div>
        </div>
        
        <div class="probabilities">
            <h3>📊 All Probabilities:</h3>
            ${probabilityBars}
        </div>
        
        <div class="tips">
            <h3>🎯 Result Explanation:</h3>
            <ul>
                <li><strong>Predicted Digit:</strong> The AI's best guess</li>
                <li><strong>Confidence:</strong> How sure the AI is</li>
                <li><strong>Probabilities:</strong> Likelihood for each digit (0-9)</li>
            </ul>
        </div>
    `;
}

