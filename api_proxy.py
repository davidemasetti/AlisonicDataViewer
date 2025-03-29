"""
API Proxy for Cloud Probe Solution

This script serves as a proxy to forward requests to the API server running on port 8000.
It listens on port 5001 to avoid conflicts with Streamlit.
"""
import os
import requests
from flask import Flask, request, jsonify, Response

# Create the Flask app
app = Flask(__name__)

# Target API server
API_SERVER = "http://localhost:8000"

@app.route('/')
def index():
    """Proxy the root endpoint"""
    try:
        response = requests.get(f"{API_SERVER}/")
        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
    except Exception as e:
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

@app.route('/api/health')
def health_check():
    """Proxy the health check endpoint"""
    try:
        response = requests.get(f"{API_SERVER}/api/health")
        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
    except Exception as e:
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

@app.route('/api/probe/data', methods=['POST'])
def receive_probe_data():
    """Proxy the probe data endpoint"""
    try:
        # Forward the exact request content and headers
        headers = {
            'Content-Type': request.headers.get('Content-Type', 'application/xml')
        }
        response = requests.post(
            f"{API_SERVER}/api/probe/data",
            data=request.data,
            headers=headers
        )
        return Response(
            response.content,
            status=response.status_code,
            content_type=response.headers.get('Content-Type', 'application/json')
        )
    except Exception as e:
        return jsonify({"error": f"Proxy error: {str(e)}"}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PROXY_PORT", 5001))
    app.run(host='0.0.0.0', port=port, debug=False)