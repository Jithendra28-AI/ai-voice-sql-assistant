
import streamlit as st
import openai
import sqlite3
import speech_recognition as sr

# OpenAI API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

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

def transcribe_voice():
    r = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Speak your question now...")
        audio = r.listen(source)
    try:
        return r.recognize_google(audio)
    except Exception as e:
        return f"Error: {str(e)}"

def generate_sql(nl_query):
    prompt = f"""Given the database with tables:
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
st.title("🗣️ Speak to SQL Assistant")
st.write("Ask your database anything using your voice.")

if st.button("🎙️ Record Voice"):
    nl_question = transcribe_voice()
    st.write("You said:", nl_question)

    sql_query = generate_sql(nl_question)
    st.code(sql_query, language="sql")

    result, columns = run_sql(sql_query)
    if isinstance(result, str):
        st.error(f"SQL Error: {result}")
    else:
        st.success("Query Result:")
        st.dataframe([dict(zip(columns, row)) for row in result])
