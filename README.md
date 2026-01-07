# Suppocket

## Your Pocket Support Solution 🎟️

Suppocket is a comprehensive, open-source support ticket management system built with Python and Streamlit. It's designed to help individuals and organizations efficiently track, manage, and resolve support requests, enhancing overall service delivery and user satisfaction.

## Features

*   **User Authentication & Authorization**: Secure login, registration, and profile management for different user roles.
*   **Centralized Dashboard**: A clear overview of all support tickets, including statuses, priorities, and assignments.
*   **Effortless Ticket Management**: Easily create, view, update, and resolve support tickets.
*   **Role-Based Access Control**: Differentiate between users and administrators with specific permissions.
*   **Analytics and Reporting**: Gain insights into ticket trends and support performance.
*   **Email Notifications**: Automated email alerts for ticket status changes (e.g., creation, assignment, resolution).
*   **Service Level Agreement (SLA) Tracking**: Manage and monitor response and resolution times.
*   **Intuitive User Interface**: Powered by Streamlit for a clean, interactive, and responsive web application.

## Project Structure

The project is organized into logical directories for maintainability and clarity:

```
.
├── app.py                      # Main Streamlit application entry point
├── auth_utils.py               # Utility functions for authentication
├── email_utils.py              # Utility functions for sending emails
├── requirements.txt            # List of Python dependencies
├── sla_utils.py                # Utility functions for SLA management
├── test_sla_utils.py           # Unit tests for SLA utilities
├── db/                         # Database related scripts and modules
│   ├── analytics_helpers.py    # Helpers for database analytics
│   ├── auth.py                 # Database operations related to authentication
│   ├── database.py             # Database connection and schema definition
│   ├── seed_tickets.py         # Script to seed initial ticket data
│   ├── seed_users.py           # Script to seed initial user data
│   └── test.py                 # Database testing utilities
├── pages/                      # Individual pages of the Streamlit application
│   ├── _Admin.py               # Admin panel page
│   ├── _Reports.py             # Reports page
│   ├── 1_Login.py              # User login page
│   ├── 2_Register.py           # New user registration page
│   ├── 3_Dashboard.py          # Main dashboard page
│   ├── 4_Tickets.py            # Page to view all tickets
│   ├── 5_Create_Ticket.py      # Page to create a new ticket
│   ├── 6_Ticket_Details.py     # Page to view details of a specific ticket
│   ├── 7_Analytics.py          # Analytics dashboard page
│   └── 8_Profile.py            # User profile page
└── templates/                  # Templates for various purposes
    └── emails/                 # HTML email templates
        ├── ticket_assigned.html
        ├── ticket_created.html
        └── ticket_resolved.html
```

## Installation Guide

Follow these steps to set up and run Suppocket locally.

### Prerequisites

*   Python 3.8+
*   `pip` (Python package installer)
*   `git` (for cloning the repository)

### 1. Clone the Repository

First, clone the Suppocket repository to your local machine:

```bash
git clone https://github.com/must-git/suppocket.git # Replace with actual repository URL
cd suppocket
```

### 2. Set up a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies:

**On Windows:**
```bash
python -m venv venv
.\venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

With your virtual environment activated, install the required Python packages:

```bash
pip install -r requirements.txt
```

### 4. Database Setup and Seeding

Suppocket uses a local database. You'll need to initialize the database and optionally seed it with some initial data:

```bash
# Initialize the database schema (if database.py contains schema creation logic)
# You might need to run a specific function or script within database.py, e.g.:
python -c "from db.database import init_db; init_db()" # Example, adjust based on actual database.py content

# Seed initial users
python db/seed_users.py

# Seed initial tickets
python db/seed_tickets.py
```
**Note:** The exact commands for database initialization might vary depending on the implementation details within `db/database.py`. The above are common patterns; you may need to inspect `db/database.py` for precise instructions if the examples don't work directly.

### 5. Running the Application

Once everything is set up, you can run the Streamlit application:

```bash
streamlit run app.py
```

This command will open the Suppocket application in your default web browser.

## Usage

After running the application, navigate to the provided URL (usually `http://localhost:8501`). You can then:
*   **Register** a new account if you don't have one.
*   **Log in** with your credentials.
*   Explore the **Dashboard**, **Tickets**, **Create Ticket**, **Analytics**, and **Profile** pages using the sidebar navigation.
*   Access the **Admin** and **Reports** pages if you have administrative privileges.
