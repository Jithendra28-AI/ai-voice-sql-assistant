import streamlit as st
import sqlite3
import pandas as pd
import os
from openai import OpenAI
import whisper
import tempfile

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
st.title("🧠 Multi-Table AI SQL Assistant with Voice + JOINs")

uploaded_files = st.file_uploader("📁 Upload one or more CSV files", type="csv", accept_multiple_files=True)
voice_file = st.file_uploader("🎙️ Upload a .wav file to ask your question by voice", type="wav")

# DB setup
db_name = "multi.db"
conn = sqlite3.connect(db_name)
table_info = {}

# Load all uploaded CSVs into SQLite
if uploaded_files:
    for file in uploaded_files:
        table_name = os.path.splitext(file.name)[0].replace(" ", "_").lower()
        df = pd.read_csv(file)
        df.to_sql(table_name, conn, if_exists="replace", index=False)
        table_info[table_name] = df.columns.tolist()
        st.success(f"✅ Loaded `{file.name}` as `{table_name}`")
        st.dataframe(df.head())

# Optional: manually define relationships
relationships = st.text_area("🔗 Define table relationships (one per line)", placeholder="parks.id = visitors.park_id")

# Build schema for prompt
def build_schema_text(table_info, rel_text):
    schema_lines = [f"{table}({', '.join(cols)})" for table, cols in table_info.items()]
    rel_lines = rel_text.strip().splitlines() if rel_text else []
    return "\n".join(["TABLES:"] + schema_lines + ["", "RELATIONSHIPS:"] + rel_lines)

# Whisper voice transcription
voice_query = ""
if voice_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(voice_file.getbuffer())
        tmp_path = tmp.name
    try:
        model = whisper.load_model("base")
        result = model.transcribe(tmp_path)
        voice_query = result["text"]
        st.success(f"🎤 Transcribed voice input: {voice_query}")
    except Exception as e:
        st.error(f"Whisper transcription failed: {str(e)}")

# Text input fallback
text_query = st.text_input("💬 Or type your question:")

# Combine voice and text (if both given, prefer text)
final_query = text_query.strip() if text_query else voice_query

# Generate SQL
def generate_sql(query, schema_text):
    prompt = f"""
You are a helpful assistant that generates SQL from natural language.

{schema_text}

Translate this question into a valid SQL query:
Question: {query}
SQL:
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You generate SQL queries with joins when needed."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=200
    )
    sql_code = response.choices[0].message.content.strip()
    sql_code = sql_code.replace("```sql", "").replace("```", "").strip()
    return sql_code

# Process query
if final_query and table_info:
    schema = build_schema_text(table_info, relationships)
    sql_query = generate_sql(final_query, schema)
    st.code(sql_query, language="sql")

    try:
        result_df = pd.read_sql_query(sql_query, conn)
        if result_df.empty:
            st.warning("⚠️ Query ran, but no results found.")
        else:
            st.success("✅ Query Result:")
            st.dataframe(result_df)

            # CSV export
            csv = result_df.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download CSV", csv, "query_result.csv", "text/csv")

            # Chart
            numeric_cols = result_df.select_dtypes(include="number").columns
            if len(numeric_cols) > 0:
                st.subheader("📊 Auto Chart")
                st.bar_chart(result_df[numeric_cols[0]])
    except Exception as e:
        st.error(f"❌ SQL Error: {str(e)}")

conn.close()
