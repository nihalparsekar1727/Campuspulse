import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

DB_NAME = "campuspulse.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS Users (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL, department TEXT NOT NULL,
            roll_no TEXT NOT NULL, password TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            description TEXT, date DATE NOT NULL, venue TEXT NOT NULL,
            max_capacity INTEGER NOT NULL, coordinator_name TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS Registrations (
            registration_id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER,
            event_id INTEGER, registration_date TIMESTAMP,
            FOREIGN KEY(student_id) REFERENCES Users(student_id),
            FOREIGN KEY(event_id) REFERENCES Events(event_id))''')
    conn.commit()
    conn.close()

init_db()

def run_query(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(query, params)
    data = c.fetchall()
    conn.commit()
    conn.close()
    return data

if 'logged_in_user' not in st.session_state:
    st.session_state['logged_in_user'] = None

st.set_page_config(page_title="CampusPulse", layout="wide")
st.title("🎓 CampusPulse: Role-Based Event Management")

st.sidebar.title("Navigation Menu")
menu_options = ["Student Registration & Login", "Event Management", "Seat Allocation", "Admin Dashboard"]
choice = st.sidebar.radio("Go to:", menu_options)

if st.session_state['logged_in_user']:
    st.sidebar.success(f"Logged in as: {st.session_state['logged_in_user']['name']}")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in_user'] = None
        st.rerun()

if choice == "Student Registration & Login":
    st.header("Student Portal")
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        login_email = st.text_input("Email Address", key="login_email")
        login_password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            user = run_query("SELECT * FROM Users WHERE email=? AND password=?", (login_email, login_password))
            if user:
                st.session_state['logged_in_user'] = {'id': user[0][0], 'name': user[0][1], 'email': user[0][2]}
                st.success(f"Welcome back, {user[0][1]}!")
                st.rerun()
            else:
                st.error("Invalid email or password.")
                
    with tab2:
        reg_name = st.text_input("Full Name")
        reg_email = st.text_input("Email Address")
        reg_dept = st.selectbox("Department", ["B.Sc. IT", "B.Sc. CS", "BMS", "BMM", "B.Com"])
        reg_roll = st.text_input("Roll Number")
        reg_pass = st.text_input("Create Password", type="password")
        if st.button("Register Student"):
            if reg_name and reg_email and reg_roll and reg_pass:
                try:
                    run_query("INSERT INTO Users (name, email, department, roll_no, password) VALUES (?, ?, ?, ?, ?)", 
                              (reg_name, reg_email, reg_dept, reg_roll, reg_pass))
                    st.success("Registration successful! You can now log in.")
                except sqlite3.IntegrityError:
                    st.error("Email already exists in the system.")
            else:
                st.warning("Please fill in all details.")

elif choice == "Event Management":
    st.header("Event Management Panel")
    with st.expander("➕ Create New Event", expanded=True):
        e_title = st.text_input("Event Title")
        e_desc = st.text_area("Event Description")
        e_date = st.date_input("Event Date")
        e_venue = st.text_input("Venue")
        e_cap = st.number_input("Maximum Capacity", min_value=1, value=50)
        e_coord = st.text_input("Coordinator Name")
        if st.button("Create Event"):
            if e_title and e_venue and e_coord:
                run_query("INSERT INTO Events (title, description, date, venue, max_capacity, coordinator_name) VALUES (?, ?, ?, ?, ?, ?)",
                          (e_title, e_desc, e_date, e_venue, e_cap, e_coord))
                st.success(f"Event '{e_title}' created successfully!")
            else:
                st.error("Please fill in all required fields.")
                
    st.subheader("Current Events Database")
    conn = sqlite3.connect(DB_NAME)
    df_events = pd.read_sql_query("SELECT * FROM Events", conn)
    conn.close()
    if not df_events.empty:
        st.dataframe(df_events, use_container_width=True)
    else:
        st.info("No events have been created yet.")

elif choice == "Seat Allocation":
    st.header("Event Registration & Seat Allocation")
    if not st.session_state['logged_in_user']:
        st.warning("You must be logged in as a student to register for events.")
    else:
        student_id = st.session_state['logged_in_user']['id']
        events = run_query("SELECT event_id, title, max_capacity FROM Events")
        if not events:
            st.info("No upcoming events available.")
        else:
            event_dict = {f"{e[1]} (ID: {e[0]})": e for e in events}
            selected_event_name = st.selectbox("Select an Event:", list(event_dict.keys()))
            selected_event = event_dict[selected_event_name]
            event_id, max_capacity = selected_event[0], selected_event[2]
            
            seats_filled = run_query("SELECT COUNT(*) FROM Registrations WHERE event_id=?", (event_id,))[0][0]
            seats_available = max_capacity - seats_filled
            
            st.write(f"**Total Capacity:** {max_capacity} | **Seats Filled:** {seats_filled} | **Seats Available:** {seats_available}")
            
            if seats_available <= 0:
                st.error("Registration Closed: Event is at maximum capacity.")
            else:
                if st.button("Confirm Registration"):
                    if run_query("SELECT * FROM Registrations WHERE student_id=? AND event_id=?", (student_id, event_id)):
                        st.warning("You are already registered for this event!")
                    else:
                        reg_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        run_query("INSERT INTO Registrations (student_id, event_id, registration_date) VALUES (?, ?, ?)", 
                                  (student_id, event_id, reg_time))
                        st.success(f"Seat Allocated! You are registered for '{selected_event[1]}'.")
                        st.balloons()

elif choice == "Admin Dashboard":
    st.header("Admin Dashboard & Analytics")
    events = run_query("SELECT event_id, title FROM Events")
    if not events:
        st.info("No events found.")
    else:
        event_dict = {f"{e[1]} (ID: {e[0]})": e[0] for e in events}
        filter_event = st.selectbox("Select Event Roster:", list(event_dict.keys()))
        selected_event_id = event_dict[filter_event]
        
        query = """
            SELECT u.student_id, u.name, u.email, u.department, u.roll_no, r.registration_date 
            FROM Users u JOIN Registrations r ON u.student_id = r.student_id
            WHERE r.event_id = ?
        """
        conn = sqlite3.connect(DB_NAME)
        df_roster = pd.read_sql_query(query, conn, params=(selected_event_id,))
        conn.close()
        
        if not df_roster.empty:
            st.write(f"Total Registered Students: **{len(df_roster)}**")
            st.dataframe(df_roster, use_container_width=True)
            csv = df_roster.to_csv(index=False).encode('utf-8')
            st.download_button("Download Roster as CSV", data=csv, file_name=f'roster_{selected_event_id}.csv', mime='text/csv')
        else:
            st.info("No students have registered for this event yet.")
