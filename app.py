import streamlit as st
import sqlite3
import pandas as pd
from openai import OpenAI
import os

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("🧠 AI SQL Explorer — Upload Any CSV, Ask Anything")

uploaded_file = st.file_uploader("📁 Upload a CSV file", type="csv")

if uploaded_file:
    # Load CSV into DataFrame
    df = pd.read_csv(uploaded_file)
    st.success("✅ File uploaded and loaded successfully.")
    st.dataframe(df.head())

    # Load into SQLite
    conn = sqlite3.connect("dynamic.db")
    df.to_sql("data", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

    # Extract column names
    column_list = df.columns.tolist()
    columns_string = ", ".join(column_list)

    # User input
    nl_question = st.text_input("💬 Ask a question about your data:")

    def generate_sql(nl_query, columns):
        prompt = f"""
You are a helpful assistant that converts natural language to SQL.

The database has one table called `data` with these columns:
{columns}

Translate the question below into an SQL query:
Question: {nl_query}
SQL:
"""

        chat_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You generate SQL queries from plain English."},
                {"role": "user", "content": prompt}
            ],
            temperature=0,
            max_tokens=150
        )

        sql_code = chat_response.choices[0].message.content.strip()
        sql_code = sql_code.replace("```sql", "").replace("```", "").strip()
        return sql_code

    # Run query
    if nl_question:
        sql_query = generate_sql(nl_question, columns_string)
        st.code(sql_query, language="sql")

        conn = sqlite3.connect("dynamic.db")
        try:
            result_df = pd.read_sql_query(sql_query, conn)
            conn.close()

            if result_df.empty:
                st.warning("⚠️ Query executed, but no results found.")
            else:
                st.success("✅ Query Result:")
                st.dataframe(result_df)

                # Download as CSV
                csv = result_df.to_csv(index=False).encode("utf-8")
                st.download_button("⬇️ Download Result as CSV", csv, "query_result.csv", "text/csv")

                # Optional: Show chart
                numeric_cols = result_df.select_dtypes(include="number").columns
                if len(numeric_cols) > 0:
                    st.subheader("📊 Auto Bar Chart")
                    st.bar_chart(result_df[numeric_cols[0]])
        except Exception as e:
            st.error(f"❌ SQL Error: {str(e)}")
