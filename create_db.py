
import sqlite3

conn = sqlite3.connect("ecommerce.db")
cursor = conn.cursor()

cursor.executescript("""
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS orders;

CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT,
    city TEXT
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT,
    price REAL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    product_id INTEGER,
    date TEXT,
    quantity INTEGER,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

INSERT INTO customers (name, city) VALUES 
('Alice', 'Denver'),
('Bob', 'Aurora'),
('Charlie', 'Centennial');

INSERT INTO products (name, price) VALUES 
('Laptop', 1200),
('Mouse', 25),
('Monitor', 300);

INSERT INTO orders (customer_id, product_id, date, quantity) VALUES 
(1, 1, '2025-06-01', 1),
(2, 2, '2025-06-02', 2),
(3, 3, '2025-06-03', 1),
(1, 3, '2025-06-05', 1);
""")

conn.commit()
conn.close()
