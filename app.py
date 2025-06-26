import streamlit as st
import sqlite3
import pandas as pd
from openai import OpenAI
import tempfile

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Run SQL
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

# Convert NL to SQL
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
    sql_code = chat_response.choices[0].message.content.strip()
    sql_code = sql_code.replace("```sql", "").replace("```", "").strip()
    return sql_code

# UI
st.title("🧠 AI SQL Assistant with Voice + Charts + Export")

# Voice recorder
audio_file = st.audio_recorder("🎙️ Click to record your question", type="audio/wav")
nl_question = ""

if audio_file:
    import speech_recognition as sr
    r = sr.Recognizer()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_file.getbuffer())
        tmp_path = tmp.name

    with sr.AudioFile(tmp_path) as source:
        audio = r.record(source)
        try:
            nl_question = r.recognize_google(audio)
            st.success(f"You said: {nl_question}")
        except sr.UnknownValueError:
            st.error("Could not understand audio.")
        except sr.RequestError:
            st.error("Speech Recognition API unavailable.")

# Fallback: text input
if not nl_question:
    nl_question = st.text_input("Or type your question here:")

# If question entered
if nl_question:
    sql_query = generate_sql(nl_question)
    st.code(sql_query, language="sql")

    result, columns = run_sql(sql_query)
    if isinstance(result, str):
        st.error(f"SQL Error: {result}")
    elif not result:
        st.warning("Query executed, but no results found.")
    else:
        st.success("✅ Query Result:")
        df = pd.DataFrame(result, columns=columns)
        st.dataframe(df)

        # CSV export button
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Download as CSV", csv, "query_result.csv", "text/csv")

        # Visualization (basic)
        if df.shape[1] >= 2:
            numeric_cols = df.select_dtypes(include='number').columns
            if len(numeric_cols) > 0:
                st.subheader("📊 Basic Visualization")
                st.bar_chart(df.set_index(df.columns[0])[numeric_cols[0]])
