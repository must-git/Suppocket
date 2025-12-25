
mock_users = [
    {'id': 1, 'email': 'customer@example.com', 'password': 'password123', 'role': 'Customer', 'name': 'John Doe'},
    {'id': 2, 'email': 'agent@example.com', 'password': 'password123', 'role': 'Support Agent', 'name': 'Jane Smith'},
    {'id': 3, 'email': 'admin@example.com', 'password': 'password123', 'role': 'Admin', 'name': 'Admin User'},
]

mock_tickets = [
    {
        'id': 'TKT-001',
        'customerId': 1,
        'title': 'Cannot login to my account',
        'description': 'I am trying to log in, but the system says "Invalid Credentials". I have reset my password twice.',
        'priority': 'High',
        'category': 'Technical Issue',
        'status': 'Open',
        'assignedTo': None,
        'createdAt': '2025-12-15T10:00:00Z',
        'updatedAt': '2025-12-15T10:00:00Z',
        'comments': [
            {'userId': 1, 'comment': 'I need urgent help, this is blocking my work.', 'createdAt': '2025-12-15T10:00:00Z'}
        ]
    },
    {
        'id': 'TKT-002',
        'customerId': 1,
        'title': 'Question about my recent invoice',
        'description': 'I received an invoice for $50, but I believe it should be $45. Can you please check?',
        'priority': 'Medium',
        'category': 'Billing Issue',
        'status': 'In Progress',
        'assignedTo': 2,
        'createdAt': '2025-12-14T14:30:00Z',
        'updatedAt': '2025-12-15T11:00:00Z',
        'comments': [
            {'userId': 1, 'comment': 'Please find the attached invoice.', 'createdAt': '2025-12-14T14:30:00Z'},
            {'userId': 2, 'comment': 'I am looking into this and will get back to you shortly.', 'createdAt': '2025-12-15T11:00:00Z'}
        ]
    },
    {
        'id': 'TKT-003',
        'customerId': 1,
        'title': 'Feature Request: Dark Mode',
        'description': 'The application is great, but a dark mode option would be easier on the eyes.',
        'priority': 'Low',
        'category': 'General Inquiry',
        'status': 'Resolved',
        'assignedTo': 2,
        'createdAt': '2025-12-10T09:00:00Z',
        'updatedAt': '2025-12-12T16:00:00Z',
        'comments': [
            {'userId': 2, 'comment': 'Thank you for the suggestion! We have added it to our product roadmap.', 'createdAt': '2025-12-12T16:00:00Z'}
        ]
    },
]

def get_user_by_id(user_id):
    for user in mock_users:
        if user['id'] == user_id:
            return user
    return None

def get_ticket_by_id(ticket_id):
    for ticket in mock_tickets:
        if ticket['id'] == ticket_id:
            return ticket
    return None

def get_user_by_email(email):
    for user in mock_users:
        if user['email'] == email:
            return user
    return None

def add_user(email, password, name, role='Customer'):
    new_id = max([u['id'] for u in mock_users]) + 1
    new_user = {'id': new_id, 'email': email, 'password': password, 'role': role, 'name': name}
    mock_users.append(new_user)
    return new_user

def add_ticket(customer_id, title, description, priority, category):
    new_id_num = len(mock_tickets) + 1
    new_id = f"TKT-{new_id_num:03d}"
    from datetime import datetime
    now = datetime.now().isoformat() + "Z"
    new_ticket = {
        'id': new_id,
        'customerId': customer_id,
        'title': title,
        'description': description,
        'priority': priority,
        'category': category,
        'status': 'Open',
        'assignedTo': None,
        'createdAt': now,
        'updatedAt': now,
        'comments': []
    }
    mock_tickets.append(new_ticket)
    return new_ticket
