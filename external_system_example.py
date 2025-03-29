"""
Example script for external systems to send probe data
to the Cloud Probe Solution API

This demonstrates how an external system would send XML data
to the API endpoint.
"""
import requests
import argparse
import sys
import os

# Path to the XML file to send
DEFAULT_XML_PATH = "attached_assets/S1-C435-S1531-20250227095734.XML"

def send_probe_data(api_url, xml_file_path):
    """
    Send XML probe data to the API
    
    Args:
        api_url: The full URL to the API endpoint
        xml_file_path: Path to the XML file to send
    
    Returns:
        bool: True if successful, False otherwise
    """
    print(f"Sending data from {xml_file_path} to {api_url}")
    
    try:
        # Read the XML file
        with open(xml_file_path, 'r') as file:
            xml_content = file.read()
        
        # Send the XML data to the API
        headers = {'Content-Type': 'application/xml'}
        response = requests.post(api_url, data=xml_content, headers=headers)
        
        # Print response details
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Send probe data to the Cloud Probe Solution API')
    parser.add_argument('--url', default='http://localhost:5001/api/probe/data', 
                        help='URL for the API endpoint')
    parser.add_argument('--file', default=DEFAULT_XML_PATH,
                        help='Path to the XML file to send')
    args = parser.parse_args()
    
    # Make sure the XML file exists
    if not os.path.exists(args.file):
        print(f"Error: XML file not found: {args.file}")
        return 1
    
    # Send the data
    success = send_probe_data(args.url, args.file)
    
    # Return exit code based on result
    if success:
        print("\nData sent successfully!")
        return 0
    else:
        print("\nFailed to send data.")
        return 1

if __name__ == "__main__":
    sys.exit(main())