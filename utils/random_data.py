from __future__ import annotations

import random
import string
import uuid

def _unique_suffix() -> str:
    return uuid.uuid4().hex[:8]

def generate_random_name(prefix: str = "Item") -> str:
    return f"{prefix}_{_unique_suffix()}"

def generate_random_code(prefix: str = "CD") -> str:
    return f"{prefix}_{_unique_suffix()}"

def generate_random_address() -> str:
    house_num = random.randint(10, 999)
    streets = ["Main St", "Broadway Ave", "Park Lane", "Link Road", "Station Road"]
    cities = ["Coimbatore", "Chennai", "Bangalore", "Mumbai"]
    return f"No. {house_num}, {random.choice(streets)}, {random.choice(cities)}"

def generate_random_postal_code() -> str:
    return "".join(["6"] + random.choices(string.digits, k=5))

def generate_random_phone() -> str:
    first_digit = str(random.choice([7, 8, 9]))
    remaining_digits = "".join(random.choices(string.digits, k=9))
    return first_digit + remaining_digits

def generate_random_email(prefix: str = "test") -> str:
    return f"{prefix}_{_unique_suffix()}@example.com"

def generate_random_description(description: str = "Item") -> str:
    return f"{description}_{_unique_suffix()}"

def generate_random_password(length: int = 12) -> str:
    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    special = "@#$%^&*!"
    
    password_char=[
        random.choice(uppercase),
        random.choice(lowercase),
        random.choice(digits),
        random.choice(special)
    ]
    
    all_pools = uppercase + lowercase + digits + special 
    password_char += random.choices(all_pools, k=length -4 )
    
    random.shuffle(password_char)
    
    return "".join(password_char)

def generate_random_unit() -> str:
    units = ["kg", "g", "mg", "L", "mL", "cm", "m", "mm", "pcs", "box", "dozen", "pair", "set", "pack"]
    return random.choice(units)

def generate_random_gst() -> str:
    """Generates a random valid GSTIN format for testing."""
    pan = (
        "".join(random.choices(string.ascii_uppercase, k=5))
        + "".join(random.choices(string.digits, k=4))
        + random.choice(string.ascii_uppercase)
    )
    return f"33{pan}1Z{random.choice(string.ascii_uppercase + string.digits)}"
