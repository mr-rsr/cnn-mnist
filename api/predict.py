"""
Vercel serverless function for MNIST digit prediction
"""
from http.server import BaseHTTPRequestHandler
import json
import numpy as np
from PIL import Image
import io
import base64
import tensorflow as tf
from tensorflow.keras.models import load_model
import os

# Global model variable
model = None

def load_trained_model():
    """Load the trained CNN model"""
    global model
    if model is None:
        try:
            # Try to load from different possible paths
            model_paths = [
                "models/mnist_cnn_model.h5",
                "../models/mnist_cnn_model.h5",
                "/var/task/models/mnist_cnn_model.h5"
            ]
            
            for path in model_paths:
                if os.path.exists(path):
                    model = load_model(path)
                    break
            
            if model is None:
                # If no model found, create a dummy response
                return None
                
        except Exception as e:
            print(f"Error loading model: {e}")
            return None
    
    return model

def preprocess_image(image_data):
    """Preprocess image for prediction"""
    try:
        # Remove data URL prefix if present
        if image_data.startswith('data:image'):
            image_data = image_data.split(',')[1]
        
        # Decode base64
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to grayscale
        image = image.convert('L')
        
        # Resize to 28x28
        image = image.resize((28, 28), Image.LANCZOS)
        
        # Convert to numpy array
        img_array = np.array(image)
        
        # Normalize to 0-1
        img_array = img_array.astype(np.float32) / 255.0
        
        # Reshape for model input (1, 28, 28, 1)
        img_array = img_array.reshape(1, 28, 28, 1)
        
        return img_array
        
    except Exception as e:
        print(f"Error preprocessing image: {str(e)}")
        return None

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Set CORS headers
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            # Read request body
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Load model
            model = load_trained_model()
            if model is None:
                response = {"error": "Model not available"}
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Get image data
            image_data = data.get('image_data')
            if not image_data:
                response = {"error": "No image data provided"}
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Preprocess image
            processed_image = preprocess_image(image_data)
            if processed_image is None:
                response = {"error": "Failed to process image"}
                self.wfile.write(json.dumps(response).encode())
                return
            
            # Make prediction
            predictions = model.predict(processed_image, verbose=0)
            predicted_digit = int(np.argmax(predictions[0]))
            confidence = float(np.max(predictions[0]))
            
            # Get all probabilities
            probabilities = {
                str(i): float(predictions[0][i]) 
                for i in range(10)
            }
            
            response = {
                "predicted_digit": predicted_digit,
                "confidence": confidence,
                "probabilities": probabilities
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            response = {"error": f"Server error: {str(e)}"}
            self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()