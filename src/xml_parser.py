import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional

class XMLParser:
    @staticmethod
    def parse_xml(xml_content: str) -> Optional[Dict]:
        try:
            root = ET.fromstring(xml_content)
            
            # Get the first probe
            probe = root.find('.//Probe')
            if probe is None:
                return None

            # Parse temperatures
            temperatures = probe.find('Temperatures')
            temp_values = []
            if temperatures is not None:
                temp_values = [float(temp.text) for temp in temperatures.findall('Temperature')]

            # Create probe data dictionary
            probe_data = {
                'customer_id': root.find('.//CustomerID').text,
                'address': probe.find('Address').text,
                'status': probe.find('Status').text,
                'datetime': probe.find('DateTime').text,
                'product': probe.find('Product').text,
                'water': probe.find('Water').text,
                'density': probe.find('Density').text,
                'phs': probe.find('Phs').text if probe.find('Phs') is not None else '',
                'discriminator': probe.find('Discriminator').text,
                'temperatures': temp_values
            }
            
            return probe_data
        except Exception as e:
            return None
