import os
from dotenv import load_dotenv
from pymongo import MongoClient

# Load environment variables
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/trackmydeal")

import certifi
ca = certifi.where()

# Connect to MongoDB with wide compatibility settings
client = MongoClient(
    MONGO_URI, 
    serverSelectionTimeoutMS=5000,
    tlsCAFile=ca,
    tlsAllowInvalidCertificates=True, # Helps bypass some handshake alerts on certain networks
    retryReads=True
)
# Explicitly specify the database name to avoid ConfigurationError if not in URI
db = client["trackmydeal"]

# Define collections
users_collection = db["users"]
products_collection = db["products"]
price_history_collection = db["price_history"]

def init_db():
    print("Database connected successfully.")
    
    # Create indexes for efficiency
    users_collection.create_index("phone_number", unique=True)
    products_collection.create_index("url")
    price_history_collection.create_index([("product_id", 1), ("timestamp", -1)])

if __name__ == "__main__":
    init_db()
