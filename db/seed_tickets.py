import sqlite3
import datetime
import hashlib
from database import get_db_connection, create_user, create_ticket, get_user, get_all_agents, update_ticket, get_tickets

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

        customer_data = [
            ("johndoe", "johndoe@example.com", "password123", 'customer'),
            ("jane_doe", "jane.doe@example.com", "password456", 'customer'),
            ("peter_jones", "peter.jones@example.com", "password789", 'customer'),
        ]
        
        for username, email, password, role in customer_data:
            if not get_user(email=email, conn=conn):
                create_user(
                    username=username,
                    email=email,
                    password_hash=hash_password(password),
                    role=role,
                    conn=conn
                )
                print(f"User '{username}' created.")
            else:
                print(f"User '{username}' already exists.")

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

        # Get agent IDs - ensure at least one agent exists
        agents = get_all_agents(conn=conn)
        if not agents:
            print("No agents found, creating one.")
            create_user(
                username="agent1",
                email="agent1@example.com",
                password_hash=hash_password("agent1pass"),
                role='agent',
                conn=conn
            )
            agents = get_all_agents(conn=conn) # Refresh agent list
            if not agents: # Fallback if agent creation somehow failed
                print("Critical Error: Failed to create agent.")
                conn.close()
                return
        
        agent_ids = [agent['id'] for agent in agents]
        
        # --- 3. Define and Create Demo Tickets ---
        print("Creating demo tickets...")
        demo_tickets_data = [
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

        # Add some more tickets for better trend visualization
        more_demo_tickets_data = [
            {
                "title": "Database connection error",
                "description": "The application frequently loses connection to the database, showing a 'connection refused' error.",
                "customer_id": customer_ids[0], "category": "Technical", "priority": "Critical"
            },
            {
                "title": "New user onboarding issue",
                "description": "New users are unable to complete the signup process; the verification email is not being sent.",
                "customer_id": customer_ids[1], "category": "User Management", "priority": "High"
            },
            {
                "title": "Improve UI responsiveness",
                "description": "The user interface feels sluggish, especially when navigating between pages. Can performance be improved?",
                "customer_id": customer_ids[2], "category": "Feature Request", "priority": "Medium"
            },
            {
                "title": "Forgot password functionality broken",
                "description": "Attempting to use the 'forgot password' link results in an internal server error.",
                "customer_id": customer_ids[0], "category": "Account Issue", "priority": "High"
            },
            {
                "title": "Request for new report type",
                "description": "We need a new report that summarizes user activity by feature usage.",
                "customer_id": customer_ids[1], "category": "Feature Request", "priority": "Low"
            },
            {
                "title": "Broken link in documentation",
                "description": "The link to the API reference in the help documentation is broken (404 error).",
                "customer_id": customer_ids[2], "category": "Bug Report", "priority": "Medium"
            },
        ]
        demo_tickets_data.extend(more_demo_tickets_data)


        ticket_count = 0
        for i, ticket_data in enumerate(demo_tickets_data):
            # Check if a similar ticket already exists to avoid duplicates
            cursor.execute("SELECT id FROM tickets WHERE title = ? AND customer_id = ?", (ticket_data['title'], ticket_data['customer_id']))
            existing_ticket_row = cursor.fetchone()

            if existing_ticket_row is None:
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
                    # Assign the ticket to an agent if it was just created and not already assigned
                    if agent_id:
                         # Use execute for direct update, as create_ticket doesn't take agent_id
                         cursor.execute("UPDATE tickets SET agent_id = ? WHERE id = ? AND agent_id IS NULL", (agent_id, ticket_id))
                    conn.commit() # Commit each ticket creation to ensure it's in DB for next step
                    ticket_count += 1
            else:
                print(f"Ticket '{ticket_data['title']}' for customer ID {ticket_data['customer_id']} already exists. Skipping creation.")
        
        # --- 4. Update a subset of tickets with resolved_at and status ---
        print("Updating a subset of tickets with resolved dates and statuses...")
        all_tickets = get_tickets() # Get all tickets, including newly created and existing ones
        
        resolved_count = 0
        for i, ticket in enumerate(all_tickets):
            # To ensure the resolved_at is always after created_at
            created_at_dt = datetime.datetime.strptime(ticket['created_at'], '%Y-%m-%d %H:%M:%S.%f')

            # Update some existing tickets to 'Resolved' or 'Closed' with varied resolved_at dates
            if i % 3 == 0 and ticket['status'] not in ['Resolved', 'Closed']: # Update approximately every third unresolved ticket
                # Simulate resolution time: current date minus some days (e.g., 1 to 10 days)
                # Ensure resolved_at is after created_at
                resolution_delta_days = (i % 10) + 1 # 1 to 10 days resolution time
                resolved_date_candidate = created_at_dt + datetime.timedelta(days=resolution_delta_days, hours=(i%24))
                
                # Make sure the resolved_date is not in the future
                if resolved_date_candidate > datetime.datetime.now():
                    resolved_date_candidate = datetime.datetime.now() - datetime.timedelta(days=(i%5)+1)
                    if resolved_date_candidate < created_at_dt: # Ensure it's still after created_at_dt
                        resolved_date_candidate = created_at_dt + datetime.timedelta(hours=1)


                # Choose status based on index for variety
                status_to_set = 'Resolved' if i % 2 == 0 else 'Closed'
                
                if update_ticket(ticket['id'], status=status_to_set, resolved_at=resolved_date_candidate.strftime('%Y-%m-%d %H:%M:%S')):
                    resolved_count += 1
                else:
                    print(f"Failed to update ticket ID {ticket['id']}.")

        conn.commit() # Final commit for any pending changes (e.g. agent assignment updates, status updates)
        print(f"Successfully created {ticket_count} new demo tickets and updated {resolved_count} existing ones with resolution data.")

    except sqlite3.Error as e:
        print(f"An error occurred during seeding: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Starting database seeding process for tickets...")
    seed_data()
    print("Seeding process complete.")
