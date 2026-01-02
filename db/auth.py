import hashlib
from .database import get_user

def verify_password(plain_password, hashed_password):
    """Verifies a plain password against a hashed one."""
    return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password

def login_user(username_or_email, password):
    """
    Authenticates a user by username/email and password.

    Args:
        username_or_email (str): The user's username or email.
        password (str): The user's plain-text password.

    Returns:
        dict: The user's data as a dictionary if authentication is successful,
              otherwise None.
    """
    # Check if the input is an email or a username
    if '@' in username_or_email:
        user = get_user(email=username_or_email)
    else:
        user = get_user(username=username_or_email)
    
    if user and verify_password(password, user['password_hash']):
        return user
        
    return None
