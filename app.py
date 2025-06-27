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

# ✅ Minimal title
st.title("🧠 AI SQL Assistant")

# 🔐 OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 📂 Upload CSVs (SQLite only)
table_info = {}
if db_type == "SQLite (local)":
    uploaded_files = st.file_uploader("📂 Upload CSV files", type="csv", accept_multiple_files=True)
    if uploaded_files:
        for file in uploaded_files:
            table_name = os.path.splitext(file.name)[0].replace(" ", "_").lower()
            df = pd.read_csv(file)
            df.to_sql(table_name, conn, if_exists="replace", index=False)
            table_info[table_name] = df.columns.tolist()
            st.success(f"✅ Loaded `{file.name}` as `{table_name}`")
            st.dataframe(df.head())
else:
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            tables = cursor.fetchall()
            for t in tables:
                table = t[0] if isinstance(t, tuple) else t
                df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 5", conn)
                table_info[table] = list(df.columns)
        except Exception as e:
            st.error(f"Could not load schema: {e}")

# 🔗 Relationships
relationships = st.text_area("🔗 Define table relationships (JOINs)", placeholder="orders.customer_id = customers.id")

# 🧠 Schema Builder
def build_schema_prompt(info, rels):
    schema = [f"{t}({', '.join(c)})" for t, c in info.items()]
    rel_lines = rels.strip().splitlines() if rels else []
    return "\n".join(["TABLES:"] + schema + ["", "RELATIONSHIPS:"] + rel_lines)

# 🤖 SQL Generator
def generate_sql(question, schema_text):
    prompt = f"""You are an assistant that writes SQL queries.\n\n{schema_text}\n\nTranslate the question: {question}\nSQL:""""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You write SQL queries using JOINs when needed."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=200
    )
    sql_code = response.choices[0].message.content.strip()
    return sql_code.replace("```sql", "").replace("```", "").strip()

# 💬 Query
text_query = st.text_input("💬 Ask your question (use exact column names):")
user_input_addition = ""
if text_query:
    user_input_addition = st.text_area("✍️ Additional data for INSERT/UPDATE")

# 🔎 Execute
if text_query and table_info and conn:
    schema = build_schema_prompt(table_info, relationships)
    full_prompt = text_query + ("\nDetails: " + user_input_addition if user_input_addition else "")
    sql_query = generate_sql(full_prompt, schema)
    st.code(sql_query, language="sql")

    write_ops = ["insert", "update", "delete", "create", "drop", "alter"]
    is_write = any(sql_query.lower().strip().startswith(op) for op in write_ops)

    if is_write:
        st.warning("⚠️ Write query detected. Confirm before execution.")
        if st.button("✅ Confirm and Run"):
            try:
                cursor = conn.cursor()
                cursor.execute(sql_query)
                conn.commit()
                st.success("✅ Executed successfully.")
            except Exception as e:
                st.error(f"❌ Execution failed: {e}")
    else:
        try:
            result_df = pd.read_sql_query(sql_query, conn)
            if result_df.empty:
                st.warning("⚠️ No data found.")
            else:
                st.success("✅ Query Result")
                st.dataframe(result_df)

                # 📥 Export
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    result_df.to_excel(writer, index=False, sheet_name="Results")
                csv_data = result_df.to_csv(index=False).encode("utf-8")

                format_opt = st.selectbox("📁 Download Format", ["Excel", "CSV"])
                if format_opt == "Excel":
                    st.download_button("📤 Excel", excel_buffer.getvalue(), "query_result.xlsx",
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.download_button("📄 CSV", csv_data, "query_result.csv", "text/csv")
        except Exception as e:
            st.error(f"❌ SQL Error: {str(e)}")

# Footer
st.markdown("---")
st.markdown("<div style='text-align:center; font-size: 0.9em;'>© 2025 AI SQL Assistant | Built by <strong>Your Name</strong></div>", unsafe_allow_html=True)
