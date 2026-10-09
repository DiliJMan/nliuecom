from django.core.validators import URLValidator

validate_web_url = URLValidator(schemes=["http", "https"])
