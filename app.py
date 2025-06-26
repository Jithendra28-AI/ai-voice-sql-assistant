import streamlit as st
import sqlite3
import pandas as pd
import os
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("🧠 Multi-Table AI SQL Assistant")

uploaded_files = st.file_uploader("📁 Upload one or more CSV files", type="csv", accept_multiple_files=True)

# SQLite DB
db_name = "multi.db"
conn = sqlite3.connect(db_name)

table_info = {}

# Load multiple tables
if uploaded_files:
    for file in uploaded_files:
        table_name = os.path.splitext(file.name)[0].replace(" ", "_").lower()
        df = pd.read_csv(file)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        table_info[table_name] = df.columns.tolist()
        st.success(f"✅ Loaded `{file.name}` into table `{table_name}`")
        st.dataframe(df.head())

# Show detected schema
if table_info:
    st.subheader("🧾 Detected Tables and Columns")
    for table, cols in table_info.items():
        st.markdown(f"**{table}**: {', '.join(cols)}")

    # Get user's question
    nl_query = st.text_input("💬 Ask a question about your data:")

    def generate_sql(query, schema_dict):
        # Build schema string
        schema_text = "\n".join([f"{table}({', '.join(cols)})" for table, cols in schema_dict.items()])
        prompt = f"""
You are a helpful assistant that converts natural language into SQL queries.

The database contains the following tables:
{schema_text}

Translate the following natural language question into a valid SQL query:
Question: {query}
SQL:
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You generate SQL queries from natural language."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=200
        )

        sql_code = response.choices[0].message.content.strip()
        sql_code = sql_code.replace("```sql", "").replace("```", "").strip()
        return sql_code

    if nl_query:
        sql_query = generate_sql(nl_query, table_info)
        st.code(sql_query, language="sql")

        try:
            result_df = pd.read_sql_query(sql_query, conn)
            if result_df.empty:
                st.warning("⚠️ Query executed, but no data returned.")
            else:
                st.success("✅ Query Result:")
                st.dataframe(result_df)

                # Download result
                csv = result_df.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Download CSV", csv, "query_result.csv", "text/csv")

                # Optional Chart
                numeric_cols = result_df.select_dtypes(include="number").columns
                if len(numeric_cols) > 0:
                    st.subheader("📊 Chart")
                    st.bar_chart(result_df[numeric_cols[0]])
        except Exception as e:
            st.error(f"SQL Error: {str(e)}")

conn.close()
