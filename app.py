import streamlit as st
import sqlite3
import pandas as pd
import tempfile
import whisper
from openai import OpenAI

# Set your OpenAI API key from Streamlit Secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
model = whisper.load_model("base")

st.title("🎙️ Voice-to-SQL Assistant (Local Microphone Version)")

# Load CSV
uploaded_file = st.file_uploader("Upload a CSV", type="csv")
if uploaded_file:
    df = pd.read_csv(uploaded_file)
    table_name = "data"
    conn = sqlite3.connect("local_voice.db")
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    st.success(f"CSV loaded into SQLite table: `{table_name}`")
    st.dataframe(df.head())
else:
    st.warning("Upload a CSV file to continue.")
    st.stop()

# Voice recorder (Streamlit Nightly/local only)
audio_data = st.audio_recorder("🎤 Record your question", type="audio/wav")

# Transcribe audio
voice_text = ""
if audio_data:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_data.getbuffer())
        tmp_path = tmp.name
    try:
        result = model.transcribe(tmp_path)
        voice_text = result["text"]
        st.success(f"🧠 Transcribed: {voice_text}")
    except Exception as e:
        st.error(f"Whisper failed: {str(e)}")

# Text override or backup
manual_input = st.text_input("Or type your question here:")
final_query = manual_input.strip() if manual_input else voice_text

# Generate SQL using GPT
def generate_sql(query, cols):
    prompt = f"""
You are a helpful assistant that generates SQL queries.

Table: data({', '.join(cols)})

Translate this question to SQL:
Question: {query}
SQL:
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=150
    )
    sql_code = response.choices[0].message.content.strip()
    sql_code = sql_code.replace("```sql", "").replace("```", "").strip()
    return sql_code

# Process input
if final_query:
    sql_query = generate_sql(final_query, df.columns.tolist())
    st.code(sql_query, language="sql")

    try:
        result = pd.read_sql_query(sql_query, conn)
        if result.empty:
            st.warning("Query ran but returned no data.")
        else:
            st.dataframe(result)
    except Exception as e:
        st.error(f"SQL Error: {str(e)}")

conn.close()
