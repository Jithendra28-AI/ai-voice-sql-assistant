import streamlit as st
import openai
import sqlite3
from openai import OpenAI

# Load API key from Streamlit Secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Run SQL query
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

# Convert natural language to SQL using OpenAI (v1 syntax)
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

    return chat_response.choices[0].message.content.strip()

# Streamlit app
st.title("🧠 Ask Your Database with AI")
st.write("Type a question and get real-time SQL results.")

nl_question = st.text_input("💬 Ask a natural language question:")

if nl_question:
    sql_query = generate_sql(nl_question)
    st.code(sql_query, language="sql")

    result, columns = run_sql(sql_query)
    if isinstance(result, str):
        st.error(f"SQL Error: {result}")
    else:
        st.success("Query Result:")
        st.dataframe([dict(zip(columns, row)) for row in result])
