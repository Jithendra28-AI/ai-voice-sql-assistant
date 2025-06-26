import streamlit as st
import openai
import sqlite3

openai.api_key = st.secrets["OPENAI_API_KEY"]

# Function to run SQL on the database
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

# Function to generate SQL from natural language using OpenAI
def generate_sql(nl_query):
    prompt = f"""
Given the database with tables:
customers(id, name, city),
products(id, name, price),
orders(id, customer_id, product_id, date, quantity)

Translate the following natural language question into SQL:
Question: {nl_query}
SQL:"""
    response = openai.Completion.create(
        engine="text-davinci-003",
        prompt=prompt,
        max_tokens=100,
        temperature=0
    )
    return response.choices[0].text.strip()

# Streamlit UI
st.title("💬 Ask Your Database (Text-Based)")
st.write("Type a question in plain English and get the result from your database.")

nl_question = st.text_input("Your question:")

if nl_question:
    sql_query = generate_sql(nl_question)
    st.code(sql_query, language="sql")

    result, columns = run_sql(sql_query)
    if isinstance(result, str):
        st.error(f"SQL Error: {result}")
    else:
        st.success("Query Result:")
        st.dataframe([dict(zip(columns, row)) for row in result])
