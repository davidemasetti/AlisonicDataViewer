import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional
import requests

class XMLParser:
    @staticmethod
    def fetch_and_parse_xml(url: str) -> Optional[Dict]:
        try:
            # Fetch XML from URL
            response = requests.get(url, timeout=5)
            response.raise_for_status()  # Raise exception for bad status codes
            xml_content = response.text

            root = ET.fromstring(xml_content)

            # Get the first probe
            probe = root.find('.//Probe')
            if probe is None:
                return None

            # Parse temperatures
            temperatures = probe.find('Temperatures')
            temp_values = []
            if temperatures is not None:
                temp_values = [float(temp.text) for temp in temperatures.findall('Temperature') if temp.text]

            # Create probe data dictionary
            probe_data = {
                'customer_id': root.find('.//CustomerID').text if root.find('.//CustomerID') is not None else '',
                'address': probe.find('Address').text if probe.find('Address') is not None else '',
                'status': probe.find('Status').text if probe.find('Status') is not None else '',
                'datetime': probe.find('DateTime').text if probe.find('DateTime') is not None else '',
                'product': probe.find('Product').text if probe.find('Product') is not None else '',
                'water': probe.find('Water').text if probe.find('Water') is not None else '',
                'density': probe.find('Density').text if probe.find('Density') is not None else '',
                'phs': probe.find('Phs').text if probe.find('Phs') is not None else '',
                'discriminator': probe.find('Discriminator').text if probe.find('Discriminator') is not None else '',
                'temperatures': temp_values
            }

            return probe_data
        except (requests.RequestException, ET.ParseError) as e:
            st.error(f"Error fetching or parsing XML: {str(e)}")
            return None