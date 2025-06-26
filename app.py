import streamlit as st
import sqlite3
import pandas as pd
import os
from openai import OpenAI
from graphviz import Digraph
import io

# 📡 Sidebar: Connect to a Live Database
st.sidebar.title("🔌 Connect to a Live Database")

db_type = st.sidebar.selectbox("Database Type", ["SQLite (local)", "PostgreSQL", "MySQL"])

conn = None  # Define connection object

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
    background-image: url("https://images.unsplash.com/photo-1506765515384-028b60a970df?auto=format&fit=crop&w=1950&q=80");
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

# 🔐 OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 🧠 App Title
st.title("🧠 AI SQL Assistant with Full Database Control")

# 📘 Help Guide
with st.expander("📘 How to use this app"):
    st.markdown("""
    1. Choose your database connection in the sidebar:
       - Use **SQLite (local)** to upload CSVs
       - Or connect to **PostgreSQL/MySQL** by entering credentials
    2. (Optional) Define table relationships (e.g., `orders.customer_id = customers.id`)
    3. Ask natural-language questions (using exact column names)
    4. Supports SELECT, INSERT, UPDATE, DELETE, CREATE, etc.
    5. View SQL, results, download Excel/CSV, schema diagram, and chart
    """)

# 📂 Upload CSVs (only if SQLite is selected)
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
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public'") if db_type == "PostgreSQL" else cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            for t in tables:
                table = t[0] if isinstance(t, tuple) else t
                df = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 5", conn)
                table_info[table] = list(df.columns)
        except Exception as e:
            st.error(f"Could not load schema: {e}")

# 🔗 Table Relationships
relationships = st.text_area("🔗 Define table relationships (JOINs, one per line)", placeholder="orders.customer_id = customers.id")

# 🧱 Schema Visualizer
if table_info:
    st.subheader("🧩 Table Schema Visualizer")
    dot = Digraph()
    for table, cols in table_info.items():
        dot.node(table, f"{table}\n" + "\n".join(cols))
    for rel in relationships.strip().splitlines():
        if "=" in rel:
            left, right = [x.strip() for x in rel.split("=")]
            lt, rt = left.split(".")[0], right.split(".")[0]
            dot.edge(lt, rt, label=rel)
    st.graphviz_chart(dot)

# 💬 User Query
text_query = st.text_input("💬 Ask your question (use exact column names):")

user_input_addition = ""
if text_query:
    user_input_addition = st.text_area(
        "✍️ Enter additional data/details for INSERT, UPDATE, etc.",
        placeholder="e.g., name = 'John', age = 30"
    )

# 🧠 Schema builder
def build_schema_prompt(info, rels):
    schema = [f"{t}({', '.join(c)})" for t, c in info.items()]
    rel_lines = rels.strip().splitlines() if rels else []
    return "\n".join(["TABLES:"] + schema + ["", "RELATIONSHIPS:"] + rel_lines)

# 🤖 GPT SQL Generator
def generate_sql(question, schema_text):
    prompt = f"""
You are an assistant that writes SQL queries.

{schema_text}

Translate the following natural language question into a valid SQL query:
Question: {question}
SQL:
"""
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

# 🔎 Query execution
if text_query and table_info and conn:
    schema = build_schema_prompt(table_info, relationships)

    full_prompt = text_query
    if user_input_addition:
        full_prompt += f"
Details: {user_input_addition}"
    sql_query = generate_sql(full_prompt, schema)
    st.code(sql_query, language="sql")

    write_ops = ["insert", "update", "delete", "create", "drop", "alter"]
    is_write = any(sql_query.lower().strip().startswith(op) for op in write_ops)

    if is_write:
    st.warning("⚠️ This appears to be a write operation.")

    # Extra warning for CREATE/ALTER
    if sql_query.lower().startswith("create") or sql_query.lower().startswith("alter"):
        st.info("📐 This will create or modify a table. Please review the SQL carefully.")

    if st.button("✅ Confirm and Execute Write Query"):
        try:
            cursor = conn.cursor()
            cursor.execute(sql_query)
            conn.commit()
            st.success("✅ Write operation executed successfully.")
        except Exception as e:
            st.error(f"❌ Error executing write query: {e}")
    else:
        st.stop()
    st.warning("⚠️ This appears to be a write operation.")

    # Extra warning for CREATE/ALTER
    if sql_query.lower().startswith("create") or sql_query.lower().startswith("alter"):
        st.info("📐 This will create or modify a table. Please review the SQL carefully.")

    if st.button("✅ Confirm and Execute Write Query"):
            try:
                cursor = conn.cursor()
                cursor.execute(sql_query)
                conn.commit()
                st.success("✅ Write operation executed successfully.")
            except Exception as e:
                st.error(f"❌ Error executing write query: {e}")
    else:
        try:
            result_df = pd.read_sql_query(sql_query, conn)
            if result_df.empty:
                st.warning("⚠️ Query ran, but no results found.")
            else:
                st.success("✅ Query Result:")
                st.dataframe(result_df)

                # 📥 CSV and Excel Export
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                    result_df.to_excel(writer, index=False, sheet_name="QueryResult")
                csv_data = result_df.to_csv(index=False).encode("utf-8")

                st.download_button("📤 Download as Excel", excel_buffer.getvalue(), "query_result.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

                st.download_button("📄 Download as CSV", csv_data, "query_result.csv", "text/csv")

                # 📊 Chart
                numeric_cols = result_df.select_dtypes(include="number").columns
                if len(numeric_cols) > 0:
                    st.subheader("📊 Visualize Data")
                    selected_col = st.selectbox("Select numeric column to visualize", numeric_cols)
                    chart_type = st.selectbox("Chart type", ["Bar Chart", "Line Chart", "Area Chart"])
                    if chart_type == "Bar Chart":
                        st.bar_chart(result_df[selected_col])
                    elif chart_type == "Line Chart":
                        st.line_chart(result_df[selected_col])
                    elif chart_type == "Area Chart":
                        st.area_chart(result_df[selected_col])
        except Exception as e:
            st.error(f"❌ SQL Error: {str(e)}")

if conn:
    conn.close()

# 📝 Footer
st.markdown("---")
st.markdown(
    "<div style='text-align:center; font-size: 0.9em;'>"
    "© 2025 AI SQL Assistant | Built by <strong>Your Name</strong> | "
    "<a href='mailto:you@example.com'>Contact</a>"
    "</div>", unsafe_allow_html=True
)
