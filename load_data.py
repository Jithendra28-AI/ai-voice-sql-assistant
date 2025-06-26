import pandas as pd
import sqlite3

# Load your National Park data
df = pd.read_csv("NationalPark_Data.csv")

# Connect to your app's database
conn = sqlite3.connect("ecommerce.db")  # You can rename this if you want a new DB

# Save the CSV data into a table called 'parks'
df.to_sql("parks", conn, if_exists="replace", index=False)

print("✅ NationalPark_Data loaded into 'parks' table.")
conn.close()
