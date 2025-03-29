"""
Test script for the Cloud Probe Solution API
"""
import requests
import argparse
import os
import sys

# Sample XML data to test with
SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<Alisonic>
  <ProtocolVersion>
    <Number>1.0</Number>
  </ProtocolVersion>
  <Site>
    <ServerID>S1</ServerID>
    <DistributorID>D1</DistributorID>
    <CustomerID>C123</CustomerID>
    <SiteID>S456</SiteID>
  </Site>
  <Probe>
    <Address>1234</Address>
    <DateTime>2025-03-28 15:30:00</DateTime>
    <ProbeStatus>0</ProbeStatus>
    <AlarmStatus>0</AlarmStatus>
    <TankStatus>0</TankStatus>
    <Product>123.45</Product>
    <Water>12.34</Water>
    <Density>840.5</Density>
    <Ullage>1234.56</Ullage>
    <Discriminator>D</Discriminator>
    <Temperatures>
      <Temperature>23.5</Temperature>
      <Temperature>24.6</Temperature>
      <Temperature>25.7</Temperature>
    </Temperatures>
  </Probe>
</Alisonic>
"""

def test_health_check(base_url):
    """Test the health check endpoint"""
    print("\nTesting health check endpoint...")
    try:
        response = requests.get(f"{base_url}/api/health")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def test_probe_data_endpoint(base_url):
    """Test the probe data endpoint with sample XML"""
    print("\nTesting probe data endpoint...")
    try:
        headers = {'Content-Type': 'application/xml'}
        response = requests.post(
            f"{base_url}/api/probe/data", 
            data=SAMPLE_XML, 
            headers=headers
        )
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test the Cloud Probe Solution API')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL for the API')
    args = parser.parse_args()
    
    print(f"Testing API at {args.url}")
    
    # Run tests
    health_check_success = test_health_check(args.url)
    probe_data_success = test_probe_data_endpoint(args.url)
    
    # Print results summary
    print("\nTest Results:")
    print(f"Health Check: {'✅ PASS' if health_check_success else '❌ FAIL'}")
    print(f"Probe Data: {'✅ PASS' if probe_data_success else '❌ FAIL'}")
    
    # Return exit code based on test results
    if health_check_success and probe_data_success:
        print("\nAll tests passed!")
        return 0
    else:
        print("\nSome tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())