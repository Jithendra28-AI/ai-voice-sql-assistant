import streamlit as st
import sqlite3
import pandas as pd
from openai import OpenAI

# ✅ Load OpenAI API key from Streamlit secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ✅ Function to run SQL on the database
def run_sql(query):
    conn = sqlite3.connect("ecommerce.db")
    cur = conn.cursor()
    try:
        cur.execute(query)
        rows = cur.fetchall()
        cols = [desc[0] for desc in cur.description]
        conn.close()
        return rows, cols
    except Exception as e:
        return str(e), []

# ✅ Function to convert natural language to SQL using OpenAI v1
def generate_sql(nl_query):
    prompt = f"""
Given the database with tables:
customers(id, name, city),
products(id, name, price),
orders(id, customer_id, product_id, date, quantity)

Translate the following natural language question into an SQL query:
Question: {nl_query}
SQL:"""

    chat_response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant that converts natural language to SQL queries."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=150
    )

    # ✅ Remove Markdown formatting (```sql ... ```)
    sql_code = chat_response.choices[0].message.content.strip()
    sql_code = sql_code.replace("```sql", "").replace("```", "").strip()
    return sql_code

# ✅ Streamlit UI
st.title("🧠 AI-Powered SQL Assistant")
st.write("Type a natural language question and get results from your database!")

# Input box
nl_question = st.text_input("💬 Ask your question:")

if nl_question:
    # Generate SQL
    sql_query = generate_sql(nl_question)
    st.code(sql_query, language="sql")

    # Run SQL
    result, columns = run_sql(sql_query)
    if isinstance(result, str):
        st.error(f"❌ SQL Error: {result}")
    else:
        st.success("✅ Query Result:")
        df = pd.DataFrame(result, columns=columns)
        st.dataframe(df)
