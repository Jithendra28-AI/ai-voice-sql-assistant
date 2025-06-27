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
import altair as alt

usage_logs = []

# 🎨 Theme Toggle
theme_mode = st.sidebar.radio("🎨 Theme", ["Light", "Dark"])

# 🧑 Track User & Send Email
if "user_logged" not in st.session_state:
    st.title("🧑 Welcome!")
    st.markdown("Please enter your name or email to continue:")
    user_input = st.text_input("Your Name or Email")
    
    if st.button("Continue") and user_input:
        st.session_state.user_id = user_input
        st.session_state.user_logged = True
        usage_logs.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "user": user_input
        })

        def send_email_report(recipient, user_logs):
            content = "\n".join([f"{log['timestamp']} - {log['user']}" for log in user_logs])
            msg = MIMEText(content)
            msg["From"] = "anumalajithendra@gmail.com"
            msg["To"] = recipient
            msg["Subject"] = "AI SQL App - User Access Log"

            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login("anumalajithendra@gmail.com", st.secrets["EMAIL_APP_PASSWORD"])
                server.send_message(msg)

        send_email_report("anumalajithendra@gmail.com", usage_logs)
        st.rerun()
    st.stop()

# Show user name in corner
st.markdown(
    f"<div style='position: fixed; top: 10px; right: 20px; color: gray;'>👋 Hello, <strong>{st.session_state.user_id}</strong></div>",
    unsafe_allow_html=True
)

# 📡 Sidebar: Connect to a Live Database
st.sidebar.title("🔌 Connect to a Live Database")
db_type = st.sidebar.selectbox("Database Type", ["SQLite (local)", "PostgreSQL", "MySQL"])
conn = None

if db_type != "SQLite (local)":
    host = st.sidebar.text_input("Host")
    port = st.sidebar.text_input("Port", value="5432" if db_type == "PostgreSQL" else "3306")
    user = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    database = st.sidebar.text_input("Database Name")
    connect_button = st.sidebar.button("Connect to Database")

    if connect_button:
        try:
            if db_type == "PostgreSQL":
                import psycopg2
                conn = psycopg2.connect(
                    host=host, port=port, user=user, password=password, dbname=database
                )
            elif db_type == "MySQL":
                import mysql.connector
                conn = mysql.connector.connect(
                    host=host, port=port, user=user, password=password, database=database
                )
            st.sidebar.success(f"✅ Connected to {db_type}")
        except Exception as e:
            st.sidebar.error(f"❌ Connection failed: {e}")
else:
    conn = sqlite3.connect("multi.db")
    st.sidebar.success("🗂️ Using local SQLite database from uploaded CSVs.")

# 🌿 Background Styling
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {
    background-image: url("");
    background-size: cover;
    background-attachment: fixed;
    background-position: center;
    background-repeat: no-repeat;
}
[data-testid="stHeader"] {
    background-color: rgba(255, 255, 255, 0);
}
section.main > div {
    background-color: rgba(255, 255, 255, 0.88);
    padding: 1rem;
    border-radius: 10px;
}
</style>
""", unsafe_allow_html=True)

if theme_mode == "Dark":
    st.markdown("""
    <style>
    body {
        background-color: #0e1117;
        color: #ffffff;
    }
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    </style>
    """, unsafe_allow_html=True)

# 🔐 OpenAI Client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 🧠 Title
st.title("🧠 AI SQL Assistant with Full Database Control")

# 📘 Help Guide
with st.expander("📘 How to use this app"):
    st.markdown("""
    1. Choose your database connection in the sidebar.
    2. Upload CSVs or Excel files (if SQLite) or connect to PostgreSQL/MySQL.
    3. Define relationships (optional).
    4. Ask natural-language questions using column names.
    5. Confirm and run write queries or preview results.
    6. Edit data directly. Visualize with Altair charts.
    """)

# 📂 Upload Files (CSV and Excel)
table_info = {}
if db_type == "SQLite (local)":
    uploaded_files = st.file_uploader("📂 Upload CSV or Excel files", type=["csv", "xlsx"], accept_multiple_files=True)
    if uploaded_files:
        for file in uploaded_files:
            table_name = os.path.splitext(file.name)[0].replace(" ", "_").lower()
            if file.name.endswith(".csv"):
                df = pd.read_csv(file)
            else:
                df = pd.read_excel(file)
            df = st.data_editor(df, num_rows="dynamic", use_container_width=True, key=table_name)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            table_info[table_name] = df.columns.tolist()
            st.success(f"✅ Loaded `{file.name}` as `{table_name}`")
else:
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_schema='public'"
                if db_type == "PostgreSQL" else "SHOW TABLES"
            )
            tables = cursor.fetchall()
            for t in tables:
                table = t[0] if isinstance(t, tuple) else t
                df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 5", conn)
                table_info[table] = list(df.columns)
        except Exception as e:
            st.error(f"Could not load schema: {e}")

# 🔗 Define Table Relationships
relationships = st.text_area("🔗 Table Relationships (e.g., orders.customer_id = customers.id)")

# 🧠 Build schema for GPT
schema = [f"{t}({', '.join(cols)})" for t, cols in table_info.items()]
schema_text = "\n".join(["TABLES:"] + schema + ["", "RELATIONSHIPS:"] + relationships.splitlines())

# 💬 Query input
query = st.text_input("💬 Ask your question (use column names from your tables):")
extra_data = st.text_area("✍️ Optional data (for INSERT/UPDATE queries)", placeholder="e.g., name = 'John', age = 30")

# Generate SQL using GPT
if query:
    prompt = f"""
You are an assistant that writes SQL queries.

{schema_text}

Translate the following natural language question into a valid SQL query:
Question: {query}
"""
    if extra_data:
        prompt += f"\nAdditional details: {extra_data}"

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You write SQL queries using JOINs when needed."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=200
    )
sql_query = response.choices[0].message.content.strip()
sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
st.code(sql_query, language="sql")

    # Execute or confirm
write_ops = ["insert", "update", "delete", "create", "drop", "alter"]
is_write = any(sql_query.lower().startswith(op) for op in write_ops)
if is_write:
        st.warning("⚠️ This appears to be a write operation.")
        if st.button("✅ Execute Write Query"):
            try:
                cursor = conn.cursor()
                cursor.execute(sql_query)
                conn.commit()
                st.success("✅ Write operation executed.")
            except Exception as e:
                st.error(f"❌ Error: {e}")
        else:
            st.stop()
else:
        try:
            df_result = pd.read_sql_query(sql_query, conn)
            st.success("✅ Query Result:")
            st.dataframe(df_result)

            # 📤 Export
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                df_result.to_excel(writer, index=False)
            csv_buf = df_result.to_csv(index=False).encode("utf-8")

            st.download_button("📤 Download Excel", excel_buf.getvalue(), "results.xlsx")
            st.download_button("📄 Download CSV", csv_buf, "results.csv")

            # 📊 Chart
            num_cols = df_result.select_dtypes(include="number").columns
            if len(num_cols) > 0:
                st.subheader("📊 Visualize")
                col = st.selectbox("Select column to plot", num_cols)
                chart = alt.Chart(df_result).mark_bar().encode(
                    x=alt.X(col, bin=True),
                    y='count()'
                )
                st.altair_chart(chart)
        except Exception as e:
            st.error(f"❌ SQL Error: {e}")



# 📝 Footer
st.markdown("---")
st.markdown(
    "<div style='text-align:center; font-size: 0.9em;'>"
    "© 2025 AI SQL Assistant | Built by <strong>Jithendra Anumala</strong> | "
    "<a href='mailto:anumalajithendra@gmail.com'>Contact</a>"
    "</div>", unsafe_allow_html=True
)
