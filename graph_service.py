import matplotlib
matplotlib.use('Agg') # Necessary for headless environments
import matplotlib.pyplot as plt
import pandas as pd
import os
from db import price_history_collection
from matplotlib.dates import DateFormatter

from bson.objectid import ObjectId

def generate_price_graph(product_id):
    """
    Generates a matplotlib graph of the historical price data for a product.
    Returns the file path to the saved graph image.
    """
    if isinstance(product_id, str):
        product_id = ObjectId(product_id)
        
    history = list(price_history_collection.find({"product_id": product_id}).sort("timestamp", 1))
    
    if not history:
        return None
        
    df = pd.DataFrame(history)
    
    plt.figure(figsize=(10, 6))
    if len(history) == 1:
        # Plot a single big dot for brand new links
        plt.plot(df['timestamp'], df['price'], marker='o', markersize=10, color='b')
        # Add a tiny bit of padding to x-axis so the dot isn't stuck on the edge
        plt.margins(x=0.1)
    else:
        # Plot standard line graph
        plt.plot(df['timestamp'], df['price'], marker='o', linestyle='-', color='b')
    
    plt.title('Product Price Trend')
    plt.xlabel('Date')
    plt.ylabel('Price (₹)')
    plt.grid(True)
    
    # Format x-axis
    plt.gca().xaxis.set_major_formatter(DateFormatter("%Y-%m-%d %H:%M"))
    plt.gcf().autofmt_xdate()
    
    os.makedirs('static/graphs', exist_ok=True)
    filepath = f"static/graphs/{product_id}.png"
    plt.savefig(filepath, bbox_inches='tight')
    plt.close()
    
    return filepath
