from datetime import datetime
from typing import Dict, Tuple, List

class DataValidator:
    @staticmethod
    def validate_probe_data(data: Dict) -> Tuple[bool, List[str]]:
        errors = []

        # ProbeStatus validation (max 2 digits)
        try:
            status = int(data['probe_status'])
            if status < 0 or len(str(status)) > 2:
                errors.append("Probe status must be a positive number with max 2 digits")
        except ValueError:
            errors.append("Probe status must be a valid integer")

        # AlarmStatus validation (0, 1, or 2)
        try:
            alarm_status = int(data['alarm_status'])
            if alarm_status not in [0, 1, 2]:
                errors.append("Alarm status must be 0 (ok), 1 (ack), or 2 (alarm)")
        except ValueError:
            errors.append("Alarm status must be a valid integer")

        # TankStatus validation (max 2 digits)
        try:
            tank_status = int(data['tank_status'])
            if tank_status < 0 or len(str(tank_status)) > 2:
                errors.append("Tank status must be a positive number with max 2 digits")
        except ValueError:
            errors.append("Tank status must be a valid integer")

        # Ullage validation (5 integers + 2 decimals)
        try:
            ullage = float(data['ullage'])
            if len(str(int(ullage))) > 5 or len(str(ullage).split('.')[1]) > 2:
                errors.append("Ullage must have max 5 integers and 2 decimals")
        except (ValueError, IndexError):
            errors.append("Invalid ullage value")

        # Product validation (5 integers + 2 decimals)
        try:
            product = float(data['product'])
            if len(str(int(product))) > 5 or len(str(product).split('.')[1]) > 2:
                errors.append("Product must have max 5 integers and 2 decimals")
        except (ValueError, IndexError):
            errors.append("Invalid product value")

        # Water validation (5 integers + 2 decimals)
        try:
            water = float(data['water'])
            if len(str(int(water))) > 5 or len(str(water).split('.')[1]) > 2:
                errors.append("Water must have max 5 integers and 2 decimals")
        except (ValueError, IndexError):
            errors.append("Invalid water value")

        # Density validation (4 integers + 2 decimals)
        try:
            density = float(data['density'])
            if len(str(int(density))) > 4 or len(str(density).split('.')[1]) > 2:
                errors.append("Density must have max 4 integers and 2 decimals")
        except (ValueError, IndexError):
            errors.append("Invalid density value")

        # Discriminator validation
        if data['discriminator'] not in ['D', 'P', 'N']:
            errors.append("Discriminator must be D, P, or N")

        # DateTime validation
        try:
            datetime.strptime(data['datetime'], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            errors.append("Invalid datetime format. Expected format: YYYY-MM-DD HH:MM:SS")

        # Temperature validation (3 integers + 1 decimal, range -30° to 80°)
        for temp in data['temperatures']:
            try:
                if len(str(int(temp))) > 3 or len(str(temp).split('.')[1]) > 1:
                    errors.append("Temperature must have max 3 integers and 1 decimal")
                if temp < -30 or temp > 80:
                    errors.append("Temperature must be between -30° and 80°")
            except (ValueError, IndexError):
                errors.append("Invalid temperature value")

        return len(errors) == 0, errors