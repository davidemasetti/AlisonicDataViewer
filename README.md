# Cloud Probe Solution

A comprehensive monitoring solution for Alisonic probes with multi-client, multi-site, and multi-probe support.

## System Architecture

The system consists of three main components:

1. **Streamlit Dashboard** (Port 5000) - The main user interface for visualizing probe data
2. **API Server** (Port 8000) - Handles receiving probe data via XML
3. **API Proxy** (Port 5001) - Forwards external requests to the API server

## Features

- Real-time monitoring of probe measurements
- Multi-client, multi-site, and multi-probe support
- Historical data tracking and visualization
- Interactive dashboard with summary and detailed views
- XML data input via API endpoint
- Automated data validation and storage

## Running the Application

### Starting the Services

The application consists of three services that work together:

1. **Streamlit Dashboard**: `python app.py` (Port 5000)
2. **API Server**: `python api_server.py` (Port 8000)
3. **API Proxy**: `python api_proxy.py` (Port 5001)

All services are configured to start automatically on replit.

### Accessing the Dashboard

The Streamlit dashboard is accessible at port 5000 (default Replit port).

## API Documentation

### Health Check Endpoint

- **URL**: `/api/health`
- **Method**: `GET`
- **Response**: JSON object with service status
- **Example Response**: `{"status": "healthy", "timestamp": "2025-03-29T17:40:46.421907"}`

### Probe Data Endpoint

- **URL**: `/api/probe/data`
- **Method**: `POST`
- **Content-Type**: `application/xml`
- **Body**: XML data conforming to the Alisonic probe format
- **Response**: JSON object with processing results
- **Example Response**: 
  ```json
  {
    "processed": 3,
    "results": [
      {"probe": "068745", "status": "success", "timestamp": "2025-03-29T18:05:26.564000"},
      {"probe": "032564", "status": "success", "timestamp": "2025-03-29T18:05:26.845811"},
      {"probe": "074585", "status": "success", "timestamp": "2025-03-29T18:05:27.121750"}
    ]
  }
  ```

## Testing the API

You can test the API using the included test scripts:

1. **General API Test**: `python test_api.py --url http://localhost:5001`
2. **External System Example**: `python external_system_example.py`

## Database Schema

The application uses a PostgreSQL database with the following tables:

- `clients`: Stores client information
- `sites`: Stores site information for each client
- `probes`: Stores probe information for each site
- `measurements`: Stores measurements from each probe

## Development Notes

- The `app.py` file contains the Streamlit dashboard code
- The `api_server.py` file contains the API server code
- The `api_proxy.py` file contains the proxy code for forwarding requests
- The `src/` directory contains utility modules
  - `database.py`: Database interaction
  - `xml_parser.py`: XML parsing logic
  - `data_validator.py`: Data validation
  - `ui_components.py`: UI rendering components
  - `utils.py`: Utility functions

## External Systems Integration

External systems can send probe data to the API endpoint at `/api/probe/data`. The data should be in XML format and conform to the Alisonic probe format. See `external_system_example.py` for an example of how to send data to the API.