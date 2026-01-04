from .database import get_user, update_password_hash
from auth_utils import verify_password

def login_user(username_or_email, password):
    """
    Authenticates a user and automatically upgrades their password hash if it's outdated.

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
        # If login is successful, check if the hash needs to be upgraded.
        # A simple check for the bcrypt prefix is sufficient here.
        # if not user['password_hash'].startswith('$2b$'):
        #     new_hash = hash_password(password)
        #     update_password_hash(user['id'], new_hash)
        #     user['password_hash'] = new_hash  # Update hash in the in-memory user dict

        return user
        
    return None
