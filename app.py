import streamlit as st
import openai
import sqlite3

# Use OpenAI API key from Streamlit secrets
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

# Function to convert natural language to SQL using OpenAI's latest API
def generate_sql(nl_query):
    prompt = f"""
Given the database with tables:
customers(id, name, city),
products(id, name, price),
orders(id, customer_id, product_id, date, quantity)

Translate the following natural language question into an SQL query:
Question: {nl_query}
SQL:"""

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant that converts natural language questions into SQL queries."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=150
    )

    return response["choices"][0]["message"]["content"].strip()

# Streamlit UI
st.title("💬 Ask Your Database (Text-Based AI)")
st.write("Type your question in natural language and get live data results from your database!")

# Input text from user
nl_question = st.text_input("🔍 Ask your question:")

if nl_question:
    # Convert to SQL
    sql_query = generate_sql(nl_question)
    st.code(sql_query, language="sql")

    # Run the SQL and show results
    result, columns = run_sql(sql_query)
    if isinstance(result, str):
        st.error(f"SQL Error: {result}")
    else:
        st.success("✅ Query Result:")
        st.dataframe([dict(zip(columns, row)) for row in result])
