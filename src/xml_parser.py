import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Optional

class XMLParser:
    @staticmethod
    def parse_xml_file(file_path: str) -> Optional[Dict]:
        try:
            # Parse XML file
            tree = ET.parse(file_path)
            root = tree.getroot()

            # Get the first probe
            probe = root.find('.//Probe')
            if probe is None:
                print("No Probe element found in XML")
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
        except Exception as e:
            print(f"Error parsing XML file: {str(e)}")
            return None