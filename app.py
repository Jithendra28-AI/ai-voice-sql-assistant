import streamlit as st
import sqlite3
import pandas as pd
import os
from openai import OpenAI
from graphviz import Digraph
import io
import datetime
import smtplib
from email.mime.text import MIMEText
usage_logs = []

# 🎨 Theme Toggle
theme_mode = st.sidebar.radio("🎨 Theme", ["Light", "Dark"])

# 🧑 Track User
if "user_logged" not in st.session_state:
    st.session_state.user_id = st.text_input("🧑 Please enter your name or email to continue")
    if st.session_state.user_id:
        st.session_state.user_logged = True
        usage_logs.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "user": st.session_state.user_id
        })
        def send_email_report(recipient, user_logs):
            content = "\n".join([f"{log['timestamp']} - {log['user']}" for log in user_logs])
            msg = MIMEText(content)
            msg["From"] = "jithendra.anumala@du.edu"
            msg["To"] = recipient
            msg["Subject"] = "AI SQL App - User Access Log"

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login("jithendra.anumala@du.edu", st.secrets["EMAIL_APP_PASSWORD"])
                server.send_message(msg)
        send_email_report("jithendra.anumala@du.edu", usage_logs)
    else:
        st.stop()
