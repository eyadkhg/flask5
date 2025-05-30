#!/usr/bin/env python3
"""
Background Removal API - Railway Deployment Version
A Flask-based API for removing backgrounds from images using the rembg library.
"""

from flask import Flask, request, jsonify, send_file
import os
import uuid
import tempfile
from werkzeug.utils import secure_filename
from rembg import remove
from PIL import Image
import io

# Initialize Flask app
app = Flask(__name__)

# Configuration for Railway
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def home():
    """Home endpoint with API information"""
    return jsonify({
        "message": "Background Removal API",
        "version": "1.0.0",
        "endpoints": {
            "health": "GET /health",
            "remove_background": "POST /remove-background"
        },
        "usage": "Send POST request to /remove-background with image file in form-data"
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify API is running"""
    return jsonify({
        "status": "healthy", 
        "message": "Background Removal API is running on Railway"
    }), 200

@app.route('/remove-background', methods=['POST'])
def remove_background():
    """
    Remove background from uploaded image
    
    Accepts an image file via POST request and returns the processed image with background removed
    """
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({"error": "No image selected"}), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            "error": f"File type not allowed. Supported types: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400
    
    try:
        # Read image directly from memory instead of saving to disk
        input_image = Image.open(file.stream)
        
        # Process the image with rembg (this may take 10-30 seconds)
        output_image = remove(input_image)
        
        # Convert to bytes for response
        img_io = io.BytesIO()
        output_image.save(img_io, 'PNG')
        img_io.seek(0)
        
        # Return the processed image
        return send_file(
            img_io, 
            mimetype='image/png',
            as_attachment=True,
            download_name=f"no_bg_{secure_filename(file.filename)}.png"
        )
    
    except Exception as e:
        app.logger.error(f"Error processing image: {str(e)}")
        return jsonify({"error": "Failed to process image", "details": str(e)}), 500

@app.errorhandler(413)
def too_large(e):
    return jsonify({"error": "File too large. Maximum size is 16MB"}), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)