import streamlit as st
import sqlite3
import pandas as pd
import os
from openai import OpenAI
from graphviz import Digraph
import io

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

# 🔐 OpenAI
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# 🧠 App Title
st.title("🧠 AI SQL Assistant with Excel + Schema Visualizer")

# 📘 Help Guide
with st.expander("📘 How to use this app"):
    st.markdown("""
    1. Upload multiple CSV files.
    2. (Optional) Define table relationships (e.g., orders.customer_id = customers.id).
    3. Ask natural-language questions (using exact column names).
    4. View SQL, table results, download Excel, see schema diagram, and plot chart.
    """)

# 📂 Upload CSVs
uploaded_files = st.file_uploader("📂 Upload CSV files", type="csv", accept_multiple_files=True)
conn = sqlite3.connect("multi.db")
table_info = {}

# 📥 Load into SQLite
if uploaded_files:
    for file in uploaded_files:
        table_name = os.path.splitext(file.name)[0].replace(" ", "_").lower()
        df = pd.read_csv(file)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        table_info[table_name] = df.columns.tolist()
        st.success(f"✅ Loaded `{file.name}` as `{table_name}`")
        st.dataframe(df.head())

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

# 🧠 GPT Schema Prompt
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

# 🔎 Execute Query
if text_query and table_info:
    schema = build_schema_prompt(table_info, relationships)
    sql_query = generate_sql(text_query, schema)
    st.code(sql_query, language="sql")

    try:
        result_df = pd.read_sql_query(sql_query, conn)
        if result_df.empty:
            st.warning("⚠️ Query ran, but no results found.")
        else:
            st.success("✅ Query Result:")
            st.dataframe(result_df)

            # 📥 Excel Export
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
                result_df.to_excel(writer, index=False, sheet_name="QueryResult")
            st.download_button("📤 Download as Excel", excel_buffer.getvalue(), "query_result.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            # 📊 Chart
            numeric_cols = result_df.select_dtypes(include="number").columns
            if len(numeric_cols) == 0:
                st.info("ℹ️ No numeric columns found for charting.")
            else:
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

conn.close()

# 📝 Footer
st.markdown("---")
st.markdown(
    "<div style='text-align:center; font-size: 0.9em;'>"
    "© 2025 AI SQL Assistant | Built by <strong>Your Name</strong> | "
    "<a href='mailto:you@example.com'>Contact</a>"
    "</div>",
    unsafe_allow_html=True
)
