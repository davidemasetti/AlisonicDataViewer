"""
API Server for Cloud Probe Solution
Provides endpoints to receive XML data from remote sources
"""
import os
import json
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Union

from flask import Flask, request, jsonify
import xml.etree.ElementTree as ET

from src.database import Database
from src.xml_parser import XMLParser
from src.data_validator import DataValidator

app = Flask(__name__)
db = Database()

@app.route('/')
def index():
    return jsonify({
        "name": "Cloud Probe Solution API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": [
            {
                "path": "/api/probe/data",
                "method": "POST",
                "description": "Submit probe data as XML"
            },
            {
                "path": "/api/health",
                "method": "GET",
                "description": "API health check"
            }
        ]
    })

@app.route('/api/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/api/probe/data', methods=['POST'])
def receive_probe_data():
    """Endpoint to receive probe data as XML"""
    if not request.data:
        return jsonify({"error": "No data received"}), 400
    
    try:
        # Process XML data
        xml_data = request.data.decode('utf-8')
        
        # Save XML to a temporary file for processing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xml') as tmp_file:
            tmp_file.write(xml_data.encode('utf-8'))
            tmp_path = tmp_file.name
        
        # Use the existing XML parser to process the file
        probe_data_list = XMLParser.parse_xml_file(tmp_path)
        
        # Clean up the temporary file
        os.unlink(tmp_path)
        
        if not probe_data_list:
            return jsonify({"error": "Failed to parse XML data"}), 400
        
        # Validate and save all probe data
        results = []
        for probe_data in probe_data_list:
            # Validate the data
            is_valid, errors = DataValidator.validate_probe_data(probe_data)
            
            if is_valid:
                # Save to database
                try:
                    db.save_measurement(probe_data)
                    results.append({
                        "probe": probe_data.get("address", ""),
                        "status": "success",
                        "timestamp": datetime.now().isoformat()
                    })
                except Exception as e:
                    results.append({
                        "probe": probe_data.get("address", ""),
                        "status": "error",
                        "error": str(e)
                    })
            else:
                results.append({
                    "probe": probe_data.get("address", ""),
                    "status": "validation_error",
                    "errors": errors
                })
        
        return jsonify({
            "processed": len(probe_data_list),
            "results": results
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("API_PORT", 8000))
    app.run(host='0.0.0.0', port=port, debug=False)