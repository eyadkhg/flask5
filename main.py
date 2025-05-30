#!/usr/bin/env python3
"""
Background Removal API - Render Deployment Version
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
import logging

# Initialize Flask app
app = Flask(__name__)

# Configuration for Render
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        "status": "running",
        "platform": "Render",
        "endpoints": {
            "health": "GET /health",
            "remove_background": "POST /remove-background",
            "docs": "GET /"
        },
        "usage": {
            "method": "POST",
            "endpoint": "/remove-background",
            "content_type": "multipart/form-data",
            "field_name": "image",
            "supported_formats": list(ALLOWED_EXTENSIONS),
            "max_file_size": "16MB"
        },
        "example": {
            "curl": "curl -X POST -F 'image=@your-image.jpg' https://your-app.onrender.com/remove-background -o result.png"
        }
    }), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint to verify API is running"""
    return jsonify({
        "status": "healthy", 
        "message": "Background Removal API is running on Render",
        "timestamp": str(uuid.uuid4()),
        "python_version": f"Python {os.sys.version.split()[0]}"
    }), 200

@app.route('/remove-background', methods=['POST'])
def remove_background():
    """
    Remove background from uploaded image
    
    Accepts an image file via POST request and returns the processed image with background removed
    """
    logger.info("Received background removal request")
    
    if 'image' not in request.files:
        logger.warning("No image file provided in request")
        return jsonify({"error": "No image file provided", "field": "image"}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        logger.warning("Empty filename provided")
        return jsonify({"error": "No image selected"}), 400
    
    if not allowed_file(file.filename):
        logger.warning(f"Unsupported file type: {file.filename}")
        return jsonify({
            "error": f"File type not allowed. Supported types: {', '.join(ALLOWED_EXTENSIONS)}",
            "filename": file.filename
        }), 400
    
    try:
        logger.info(f"Processing image: {file.filename}")
        
        # Read image directly from memory (no disk storage needed)
        input_image = Image.open(file.stream)
        
        # Log image info
        logger.info(f"Image size: {input_image.size}, format: {input_image.format}, mode: {input_image.mode}")
        
        # Process the image with rembg (this may take 10-60 seconds)
        logger.info("Starting background removal process...")
        output_image = remove(input_image)
        logger.info("Background removal completed")
        
        # Convert to bytes for response
        img_io = io.BytesIO()
        output_image.save(img_io, 'PNG')
        img_io.seek(0)
        
        # Generate filename for download
        original_name = secure_filename(file.filename)
        base_name = os.path.splitext(original_name)[0]
        download_filename = f"{base_name}_no_background.png"
        
        logger.info(f"Sending processed image: {download_filename}")
        
        # Return the processed image
        return send_file(
            img_io, 
            mimetype='image/png',
            as_attachment=True,
            download_name=download_filename
        )
    
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error processing image: {error_msg}")
        return jsonify({
            "error": "Failed to process image", 
            "details": error_msg,
            "filename": file.filename if file else "unknown"
        }), 500

@app.errorhandler(413)
def too_large(e):
    logger.warning("File too large uploaded")
    return jsonify({
        "error": "File too large", 
        "max_size": "16MB",
        "tip": "Please compress your image or use a smaller file"
    }), 413

@app.errorhandler(404)
def not_found(e):
    return jsonify({
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/health", "/remove-background"]
    }), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal server error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))  # Render uses port 10000 by default
    app.run(host='0.0.0.0', port=port, debug=False)