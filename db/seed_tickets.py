
import sqlite3
import datetime
import hashlib
from .database import get_db_connection, create_user, create_ticket, get_user, get_all_agents

def hash_password(password):
    """Hashes a password using SHA256."""
    return hashlib.sha256(password.encode()).hexdigest()

def seed_data():
    """
    Seeds the database with initial demo tickets and additional customer users.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # --- 1. Add New Customer Users ---
        print("Creating additional customer users...")

        # Customer 1 (the one that was missing)
        customer1_username = "johndoe"
        customer1_email = "johndoe@example.com"
        customer1_password = "password123"
        if not get_user(email=customer1_email, conn=conn):
            create_user(
                username=customer1_username,
                email=customer1_email,
                password_hash=hash_password(customer1_password),
                role='customer',
                conn=conn
            )
            print(f"User '{customer1_username}' created.")
        else:
            print(f"User '{customer1_username}' already exists.")
        
        # Customer 2
        customer2_username = "jane_doe"
        customer2_email = "jane.doe@example.com"
        customer2_password = "password456"
        if not get_user(username=customer2_username, conn=conn):
            create_user(
                username=customer2_username,
                email=customer2_email,
                password_hash=hash_password(customer2_password),
                role='customer',
                conn=conn
            )
            print(f"User '{customer2_username}' created.")
        else:
            print(f"User '{customer2_username}' already exists.")

        # Customer 3
        customer3_username = "peter_jones"
        customer3_email = "peter.jones@example.com"
        customer3_password = "password789"
        if not get_user(username=customer3_username, conn=conn):
            create_user(
                username=customer3_username,
                email=customer3_email,
                password_hash=hash_password(customer3_password),
                role='customer',
                conn=conn
            )
            print(f"User '{customer3_username}' created.")
        else:
            print(f"User '{customer3_username}' already exists.")

        # --- 2. Get User and Agent IDs ---
        print("Fetching user and agent IDs for ticket creation...")
        
        # Get customer IDs
        customer1 = get_user(email="johndoe@example.com", conn=conn)
        customer2 = get_user(username="jane_doe", conn=conn)
        customer3 = get_user(username="peter_jones", conn=conn)
        
        if not all([customer1, customer2, customer3]):
            print("Error: Could not find all customer users. Aborting ticket seeding.")
            return

        customer_ids = [customer1['id'], customer2['id'], customer3['id']]

        # Get agent IDs
        agents = get_all_agents(conn=conn)
        agent_ids = [agent['id'] for agent in agents]
        
        if not agent_ids:
            print("Warning: No agents found in the database. Tickets will be unassigned.")
            # Handle case with no agents if necessary, maybe assign None
            agent_ids.append(None)


        # --- 3. Define and Create Demo Tickets ---
        print("Creating demo tickets...")
        demo_tickets = [
            # Customer 1 Tickets
            {
                "title": "Cannot log in to my account",
                "description": "Every time I try to log in, I get an 'Invalid Credentials' error, but I'm sure my password is correct.",
                "customer_id": customer_ids[0],
                "category": "Account Issue", "priority": "High"
            },
            {
                "title": "Feature Request: Dark Mode",
                "description": "The application interface is very bright. I would love to have a dark mode option to reduce eye strain.",
                "customer_id": customer_ids[0],
                "category": "Feature Request", "priority": "Low"
            },
            # Customer 2 Tickets
            {
                "title": "Website is loading very slowly",
                "description": "For the past few days, the main dashboard has been taking over 30 seconds to load after I log in.",
                "customer_id": customer_ids[1],
                "category": "Performance", "priority": "Medium"
            },
            {
                "title": "Billing question about my last invoice",
                "description": "I was charged twice for my subscription this month. Can someone please look into invoice #INV-12345?",
                "customer_id": customer_ids[1],
                "category": "Billing", "priority": "High"
            },
            # Customer 3 Tickets
            {
                "title": "Export to PDF feature not working",
                "description": "When I click the 'Export to PDF' button on the reports page, it shows a loading spinner forever and nothing happens.",
                "customer_id": customer_ids[2],
                "category": "Bug Report", "priority": "Critical"
            },
            {
                "title": "How do I reset my API token?",
                "description": "I need to reset my API access token for security reasons but I can't find the option in my profile settings.",
                "customer_id": customer_ids[2],
                "category": "General Inquiry", "priority": "Low"
            },
        ]

        ticket_count = 0
        for i, ticket_data in enumerate(demo_tickets):
            # Check if a similar ticket already exists to avoid duplicates
            cursor.execute("SELECT id FROM tickets WHERE title = ? AND customer_id = ?", (ticket_data['title'], ticket_data['customer_id']))
            if cursor.fetchone() is None:
                # Assign agent in a round-robin fashion
                agent_id = agent_ids[i % len(agent_ids)] if agent_ids and agent_ids[0] is not None else None

                ticket_id = create_ticket(
                    title=ticket_data['title'],
                    description=ticket_data['description'],
                    customer_id=ticket_data['customer_id'],
                    category=ticket_data['category'],
                    priority=ticket_data['priority'],
                    conn=conn
                )
                if ticket_id:
                    # Assign the ticket to an agent
                    if agent_id:
                         cursor.execute("UPDATE tickets SET agent_id = ? WHERE id = ?", (agent_id, ticket_id))
                    ticket_count += 1
            else:
                print(f"Ticket '{ticket_data['title']}' for customer ID {ticket_data['customer_id']} already exists. Skipping.")
        
        conn.commit()
        print(f"Successfully created {ticket_count} new demo tickets.")

    except sqlite3.Error as e:
        print(f"An error occurred during seeding: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting database seeding process for tickets...")
    seed_data()
    print("Seeding process complete.")
