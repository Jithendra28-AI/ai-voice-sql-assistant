import streamlit as st
import sqlite3
import pandas as pd
import os
from openai import OpenAI

# 🔑 Set up OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 🧠 Title
st.title("🧠 Multi-Table AI SQL Assistant (Text Input Only)")

# 📘 Guide section
with st.expander("📘 How to use this app"):
    st.markdown("""
    **Welcome to the AI SQL Assistant!**

    1. **Upload CSV files** — Upload one or more `.csv` files.
    2. *(Optional)* Define relationships if the data is relational.
    3. **Ask questions** — Examples:
       - `"Which parks were established before 1950?"`
       - `"Total visitors by state?"`
    4. **See output** — You’ll get:
       - Generated SQL
       - Query results
       - Optional chart
       - CSV download
    """)

# 📁 Upload multiple CSV files
uploaded_files = st.file_uploader("📁 Upload one or more CSV files", type="csv", accept_multiple_files=True)

# 🔗 SQLite setup
db_name = "multi.db"
conn = sqlite3.connect(db_name)
table_info = {}

# 📥 Load uploaded CSVs into SQLite
if uploaded_files:
    for file in uploaded_files:
        table_name = os.path.splitext(file.name)[0].replace(" ", "_").lower()
        df = pd.read_csv(file)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        table_info[table_name] = df.columns.tolist()
        st.success(f"✅ Loaded `{file.name}` as `{table_name}`")
        st.dataframe(df.head())

# 🔗 Optional: manual JOIN relationships
relationships = st.text_area(
    "🔗 Define table relationships (JOINs, one per line)",
    placeholder="parks.id = visitors.park_id"
)

# 📐 Build schema text for GPT prompt
def build_schema_text(table_info, rel_text):
    schema_lines = [f"{table}({', '.join(cols)})" for table, cols in table_info.items()]
    rel_lines = rel_text.strip().splitlines() if rel_text else []
    return "\n".join(["TABLES:"] + schema_lines + ["", "RELATIONSHIPS:"] + rel_lines)

# 💬 User input
text_query = st.text_input("💬 Ask your question about the data:")

# 🔁 Generate SQL from GPT
def generate_sql(query, schema_text):
    prompt = f"""
You are an assistant that writes SQL queries.

{schema_text}

Translate the following natural language question into a valid SQL query:
Question: {query}
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
    sql_code = sql_code.replace("```sql", "").replace("```", "").strip()
    return sql_code

# 🔍 Process user query
if text_query and table_info:
    schema = build_schema_text(table_info, relationships)
    sql_query = generate_sql(text_query, schema)
    st.code(sql_query, language="sql")

    try:
        result_df = pd.read_sql_query(sql_query, conn)
        if result_df.empty:
            st.warning("⚠️ Query ran, but returned no results.")
        else:
            st.success("✅ Query Result:")
            st.dataframe(result_df)

            # 📥 Download CSV
            csv = result_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv, "query_result.csv", "text/csv")

            # 📊 Chart if numeric data exists
            numeric_cols = result_df.select_dtypes(include="number").columns
            if len(numeric_cols) > 0:
                st.subheader("📊 Auto Chart")
                st.bar_chart(result_df[numeric_cols[0]])
    except Exception as e:
        st.error(f"❌ SQL Error: {str(e)}")

# 🛑 Close DB connection
conn.close()

# 📎 Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; font-size: 0.9em;'>"
    "© 2025 AI SQL Assistant | Built by <strong>Your Name</strong> | "
    "<a href='mailto:you@example.com'>Contact</a>"
    "</div>",
    unsafe_allow_html=True
)
