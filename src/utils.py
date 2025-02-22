from datetime import datetime

def format_datetime(dt_str: str) -> str:
    try:
        dt = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        return dt_str

def get_status_color(status: str) -> str:
    try:
        status_int = int(status)
        if status_int == 0:
            return "green"
        elif status_int < 50:
            return "yellow"
        else:
            return "red"
    except ValueError:
        return "gray"