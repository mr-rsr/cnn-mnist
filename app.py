from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import numpy as np
import cv2
from PIL import Image
import io
import base64
import tensorflow as tf
from tensorflow.keras.models import load_model
import os

app = Flask(__name__, static_folder='public')
CORS(app)

# Global model variable
model = None

def load_trained_model():
    """Load the trained CNN model"""
    global model
    model_path = "models/mnist_cnn_model.h5"
    
    if os.path.exists(model_path):
        model = load_model(model_path)
        print(f"Model loaded from {model_path}")
        return True
    else:
        print(f"Model not found at {model_path}")
        return False

def preprocess_image(image_data):
    """Preprocess uploaded image for prediction with improved accuracy"""
    try:
        # Convert base64 to PIL Image if needed
        if isinstance(image_data, str):
            # Remove data URL prefix if present
            if image_data.startswith('data:image'):
                image_data = image_data.split(',')[1]
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
        else:
            image = Image.open(image_data)
        
        # Convert to grayscale
        image = image.convert('L')
        
        # Convert to numpy array for processing
        img_array = np.array(image)
        
        # For canvas drawings: white strokes on black background
        # Check if we need to invert (if background is brighter than strokes)
        if np.mean(img_array) > 127:
            img_array = 255 - img_array
        
        # Find bounding box of the digit to center it properly
        # This is crucial for MNIST accuracy
        rows = np.any(img_array > 50, axis=1)
        cols = np.any(img_array > 50, axis=0)
        
        if rows.any() and cols.any():
            rmin, rmax = np.where(rows)[0][[0, -1]]
            cmin, cmax = np.where(cols)[0][[0, -1]]
            
            # Extract the digit with some padding
            digit = img_array[rmin:rmax+1, cmin:cmax+1]
            
            # Create a square image with the digit centered
            size = max(digit.shape[0], digit.shape[1])
            # Add 20% padding
            size = int(size * 1.2)
            
            # Create black square
            square = np.zeros((size, size), dtype=np.uint8)
            
            # Center the digit in the square
            y_offset = (size - digit.shape[0]) // 2
            x_offset = (size - digit.shape[1]) // 2
            square[y_offset:y_offset+digit.shape[0], x_offset:x_offset+digit.shape[1]] = digit
            
            # Convert back to PIL for resizing
            image = Image.fromarray(square)
        
        # Resize to 28x28 with high-quality resampling
        image = image.resize((28, 28), Image.Resampling.LANCZOS)
        
        # Convert back to numpy array
        img_array = np.array(image)
        
        # Normalize to 0-1 range
        img_array = img_array.astype(np.float32) / 255.0
        
        # Apply minimal smoothing only if needed (reduce noise without losing detail)
        try:
            from scipy import ndimage
            # Very light smoothing to reduce pixelation
            img_array = ndimage.gaussian_filter(img_array, sigma=0.3)
        except ImportError:
            pass
        
        # Ensure values are in valid range
        img_array = np.clip(img_array, 0, 1)
        
        # Reshape for model input (1, 28, 28, 1)
        img_array = img_array.reshape(1, 28, 28, 1)
        
        return img_array
        
    except Exception as e:
        print(f"Error preprocessing image: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

@app.route('/')
def home():
    """Serve the main HTML interface"""
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/script.js')
def serve_script():
    """Serve the JavaScript file"""
    return send_from_directory(app.static_folder, 'script.js')

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files from public folder"""
    return send_from_directory(app.static_folder, filename)

@app.route('/debug')
def debug():
    """Serve debug test page"""
    return send_from_directory('.', 'test_debug.html')

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "message": "MNIST CNN API is running",
        "model_loaded": model is not None
    })

@app.route('/predict', methods=['POST'])
def predict():
    """Predict digit from uploaded image"""
    global model
    
    if model is None:
        return jsonify({"error": "Model not loaded"}), 500
    
    try:
        # Get image from request
        request_json = request.get_json()
        if 'image' not in request.files and (not request_json or 'image_data' not in request_json):
            return jsonify({"error": "No image provided"}), 400
        
        # Handle file upload
        if 'image' in request.files:
            image_file = request.files['image']
            if image_file.filename == '':
                return jsonify({"error": "No image selected"}), 400
            
            # Preprocess image
            processed_image = preprocess_image(image_file)
        
        # Handle base64 image data
        elif request_json and 'image_data' in request_json:
            image_data = request_json['image_data']
            processed_image = preprocess_image(image_data)
        
        if processed_image is None:
            return jsonify({"error": "Failed to process image"}), 400
        
        # Make prediction
        predictions = model.predict(processed_image, verbose=0)
        predicted_digit = int(np.argmax(predictions[0]))
        confidence = float(np.max(predictions[0]))
        
        # Get all probabilities
        probabilities = {
            str(i): float(predictions[0][i]) 
            for i in range(10)
        }
        
        return jsonify({
            "predicted_digit": predicted_digit,
            "confidence": confidence,
            "probabilities": probabilities
        })
        
    except Exception as e:
        return jsonify({"error": f"Prediction failed: {str(e)}"}), 500

@app.route('/model/info')
def model_info():
    """Get model information"""
    global model
    
    if model is None:
        return jsonify({"error": "Model not loaded"}), 500
    
    try:
        return jsonify({
            "model_summary": str(model.summary()),
            "input_shape": model.input_shape,
            "output_shape": model.output_shape
        })
    except Exception as e:
        return jsonify({"error": f"Failed to get model info: {str(e)}"}), 500

if __name__ == '__main__':
    # Load model on startup
    if not load_trained_model():
        print("Warning: Model not loaded. Train and save a model first.")
    
    app.run(debug=True, host='0.0.0.0', port=5000)