import streamlit as st
import sqlite3
import pandas as pd
import os
from openai import OpenAI

# 🌄 Background image + styling
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

# 🔑 OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 🧠 App title
st.title("🧠 Multi-Table AI SQL Assistant (Text Input Only)")

# 📘 Guide
with st.expander("📘 How to use this app"):
    st.markdown("""
    **Welcome to the AI SQL Assistant!**

    1. **Upload CSV files** — Upload one or more `.csv` files.
    2. *(Optional)* Define relationships between tables (like foreign key joins).
    3. **Ask questions** — Use natural language based on the actual column names in your data.
    
    ⚠️ **Important**: Your questions must use **exact column names** as they appear in your data.  
    Example: If your column is `YearEstablished`, don’t ask about `yearestablished` or `year`.

    4. **See results** — SQL, answers, chart, and CSV download.
    """)

# 📁 File uploader
uploaded_files = st.file_uploader("📁 Upload one or more CSV files", type="csv", accept_multiple_files=True)

# 🛠 SQLite setup
db_name = "multi.db"
conn = sqlite3.connect(db_name)
table_info = {}

# 📥 Load uploaded files
if uploaded_files:
    for file in uploaded_files:
        table_name = os.path.splitext(file.name)[0].replace(" ", "_").lower()
        df = pd.read_csv(file)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        table_info[table_name] = df.columns.tolist()
        st.success(f"✅ Loaded `{file.name}` as `{table_name}`")
        st.dataframe(df.head())

# 🔗 Relationship input
relationships = st.text_area("🔗 Define table relationships (JOINs, one per line)", placeholder="parks.id = visitors.park_id")

# 🧱 Schema builder
def build_schema_text(table_info, rel_text):
    schema_lines = [f"{table}({', '.join(cols)})" for table, cols in table_info.items()]
    rel_lines = rel_text.strip().splitlines() if rel_text else []
    return "\n".join(["TABLES:"] + schema_lines + ["", "RELATIONSHIPS:"] + rel_lines)

# 💬 User input
text_query = st.text_input("💬 Ask your question about the data:")

# 🤖 SQL generator
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

# 🔍 Query execution
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

           # 📊 Chart options
numeric_cols = result_df.select_dtypes(include="number").columns

if len(numeric_cols) == 0:
    st.info("ℹ️ No numeric columns found in the result, so no chart was generated.")
else:
    st.subheader("📊 Visualize Your Data")
    st.write("Numeric columns detected:", list(numeric_cols))  # 🧪 Debug line
    chart_col = st.selectbox("Select column to visualize", numeric_cols)
    chart_type = st.selectbox("Choose chart type", ["Bar Chart", "Line Chart", "Area Chart"])

    if chart_type == "Bar Chart":
        st.bar_chart(result_df[chart_col])
    elif chart_type == "Line Chart":
        st.line_chart(result_df[chart_col])
    elif chart_type == "Area Chart":
        st.area_chart(result_df[chart_col])
    except Exception as e:
        st.error(f"❌ SQL Error: {str(e)}")

# 🔚 Close connection
conn.close()

# 📝 Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; font-size: 0.9em;'>"
    "© 2025 AI SQL Assistant | Built by <strong>Your Name</strong> | "
    "<a href='mailto:you@example.com'>Contact</a>"
    "</div>",
    unsafe_allow_html=True
)
