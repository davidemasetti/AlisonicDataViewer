from datetime import datetime
from typing import Dict, Tuple, List

class DataValidator:
    @staticmethod
    def validate_probe_data(data: Dict) -> Tuple[bool, List[str]]:
        errors = []

        # ProbeStatus validation (max 2 digits)
        try:
            probe_status = int(data.get('probe_status', ''))
            if probe_status < 0 or len(str(probe_status)) > 2:
                errors.append("Probe status must be a positive number with max 2 digits")
        except (ValueError, TypeError):
            errors.append("Probe status must be a valid integer")

        # AlarmStatus validation (0, 1, or 2)
        try:
            alarm_status = int(data.get('alarm_status', ''))
            if alarm_status not in [0, 1, 2]:
                errors.append("Alarm status must be 0 (ok), 1 (ack), or 2 (alarm)")
        except (ValueError, TypeError):
            errors.append("Alarm status must be a valid integer")

        # TankStatus validation (max 2 digits)
        try:
            tank_status = int(data.get('tank_status', ''))
            if tank_status < 0 or len(str(tank_status)) > 2:
                errors.append("Tank status must be a positive number with max 2 digits")
        except (ValueError, TypeError):
            errors.append("Tank status must be a valid integer")

        # Ullage validation (5 integers + 2 decimals)
        try:
            ullage = float(data.get('ullage', '0.0'))
            ullage_str = str(ullage)
            int_part, dec_part = ullage_str.split('.')
            if len(int_part) > 5 or len(dec_part) > 2:
                errors.append("Ullage must have max 5 integers and 2 decimals")
        except (ValueError, IndexError):
            errors.append("Invalid ullage value")

        # Product validation (5 integers + 2 decimals)
        try:
            product = float(data.get('product', '0.0'))
            product_str = str(product)
            int_part, dec_part = product_str.split('.')
            if len(int_part) > 5 or len(dec_part) > 2:
                errors.append("Product must have max 5 integers and 2 decimals")
        except (ValueError, IndexError):
            errors.append("Invalid product value")

        # Water validation (5 integers + 2 decimals)
        try:
            water = float(data.get('water', '0.0'))
            water_str = str(water)
            int_part, dec_part = water_str.split('.')
            if len(int_part) > 5 or len(dec_part) > 2:
                errors.append("Water must have max 5 integers and 2 decimals")
        except (ValueError, IndexError):
            errors.append("Invalid water value")

        # Density validation (4 integers + 2 decimals)
        try:
            density = float(data.get('density', '0.0'))
            density_str = str(density)
            int_part, dec_part = density_str.split('.')
            if len(int_part) > 4 or len(dec_part) > 2:
                errors.append("Density must have max 4 integers and 2 decimals")
        except (ValueError, IndexError):
            errors.append("Invalid density value")

        # Discriminator validation
        discriminator = data.get('discriminator', '')
        if discriminator not in ['D', 'P', 'N']:
            errors.append("Discriminator must be D, P, or N")

        # DateTime validation
        try:
            datetime.strptime(data.get('datetime', ''), '%Y-%m-%d %H:%M:%S')
        except ValueError:
            errors.append("Invalid datetime format. Expected format: YYYY-MM-DD HH:MM:SS")

        # Temperature validation (3 integers + 1 decimal, range -30° to 80°)
        for temp in data.get('temperatures', []):
            try:
                temp_str = str(float(temp))
                int_part, dec_part = temp_str.split('.')
                if len(int_part) > 3 or len(dec_part) > 1:
                    errors.append("Temperature must have max 3 integers and 1 decimal")
                if float(temp) < -30 or float(temp) > 80:
                    errors.append("Temperature must be between -30° and 80°")
            except (ValueError, IndexError):
                errors.append("Invalid temperature value")

        return len(errors) == 0, errors