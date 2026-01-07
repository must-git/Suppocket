import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
from db.database import get_system_settings, get_ticket_by_id, get_user

# Load environment variables from .env file
load_dotenv()

def load_email_config():
    """
    Loads email configuration from the database and environment variables.
    """
    config = get_system_settings()
    config['smtp_password'] = os.getenv('SMTP_PASSWORD')
    return config

def get_email_template(template_name, context):
    """
    Renders an email template with the given context.
    """
    try:
        # This path is relative to the project root.
        template_path = os.path.join('templates', 'emails', f'{template_name}.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            template_str = f.read()
        
        # Simple string replacement for templating
        for key, value in context.items():
            template_str = template_str.replace(f'{{{{ {key} }}}}', str(value))
            
        return template_str
    except FileNotFoundError:
        print(f"Error: Email template '{template_name}.html' not found at {template_path}")
        return f"<p>Error: Email template '{template_name}.html' not found.</p>"
    except Exception as e:
        print(f"Error rendering email template: {e}")
        return f"<p>Error rendering email template.</p>"

def send_email(to_email, subject, body_html, body_text=None):
    """
    Sends an email using the configured SMTP settings.
    """
    config = load_email_config()

    if not config.get('email_enabled') or config.get('email_enabled', 'False').lower() != 'true':
        print("Email notifications are disabled.")
        return False

    # Validate essential config
    required_keys = ['smtp_host', 'smtp_port', 'smtp_username', 'smtp_password', 'from_email', 'from_name']
    if not all(k in config and config[k] for k in required_keys):
        print("Email configuration is incomplete. Cannot send email.")
        return False

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = f"{config['from_name']} <{config['from_email']}>"
    msg['To'] = to_email

    # Attach parts
    if body_text:
        msg.attach(MIMEText(body_text, 'plain'))
    if body_html:
        msg.attach(MIMEText(body_html, 'html'))
    
    if not msg.get_payload():
        print("Email has no content to send.")
        return False

    try:
        server = smtplib.SMTP(config['smtp_host'], int(config['smtp_port']))
        server.starttls()
        server.login(config['smtp_username'], config['smtp_password'])
        server.sendmail(config['from_email'], to_email, msg.as_string())
        server.quit()
        print(f"Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        # Here we could log the error to a database or file
        return False

def send_ticket_created_notification(ticket_id):
    """
    Fetches ticket data and sends a 'ticket created' notification to the customer.
    """
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        print(f"Cannot send creation notification: Ticket ID {ticket_id} not found.")
        return

    customer = get_user(user_id=ticket['customer_id'])
    if not customer or not customer.get('email'):
        print(f"Cannot send creation notification: Customer for ticket {ticket_id} not found or has no email.")
        return

    config = load_email_config()
    
    context = {
        "ticket_id": ticket['id'],
        "ticket_title": ticket['title'],
        "customer_name": customer['username'],
        "ticket_priority": ticket['priority'],
        "ticket_category": ticket['category'],
        "from_name": config.get('from_name', 'Suppocket Support')
    }

    subject = f"[Ticket #{ticket['id']}] Your ticket has been created"
    body_html = get_email_template('ticket_created', context)

    send_email(to_email=customer['email'], subject=subject, body_html=body_html)

def send_ticket_assigned_notification(ticket_id):
    """
    Fetches ticket data and sends a 'ticket assigned' notification to the agent.
    """
    ticket = get_ticket_by_id(ticket_id)
    if not ticket or not ticket.get('agent_id'):
        print(f"Cannot send assignment notification: Ticket {ticket_id} not found or no agent assigned.")
        return

    agent = get_user(user_id=ticket['agent_id'])
    if not agent or not agent.get('email'):
        print(f"Cannot send assignment notification: Agent for ticket {ticket_id} not found or has no email.")
        return
        
    customer = get_user(user_id=ticket['customer_id'])

    config = load_email_config()
    
    context = {
        "ticket_id": ticket['id'],
        "ticket_title": ticket['title'],
        "agent_name": agent['username'],
        "ticket_priority": ticket['priority'],
        "customer_name": customer['username'] if customer else 'N/A'
    }

    subject = f"You have been assigned a new ticket: #{ticket['id']}"
    body_html = get_email_template('ticket_assigned', context)

    send_email(to_email=agent['email'], subject=subject, body_html=body_html)

def send_ticket_resolved_notification(ticket_id):
    """
    Fetches ticket data and sends a 'ticket resolved' notification to the customer.
    """
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        print(f"Cannot send resolved notification: Ticket ID {ticket_id} not found.")
        return

    customer = get_user(user_id=ticket['customer_id'])
    if not customer or not customer.get('email'):
        print(f"Cannot send resolved notification: Customer for ticket {ticket_id} not found or has no email.")
        return

    config = load_email_config()
    
    context = {
        "ticket_id": ticket['id'],
        "ticket_title": ticket['title'],
        "customer_name": customer['username'],
        "from_name": config.get('from_name', 'Suppocket Support')
    }

    subject = f"[Ticket #{ticket['id']}] Your ticket has been resolved"
    body_html = get_email_template('ticket_resolved', context)

    send_email(to_email=customer['email'], subject=subject, body_html=body_html)
