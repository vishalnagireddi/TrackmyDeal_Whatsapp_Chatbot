import pandas as pd
from datetime import timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from db import price_history_collection
from sklearn.linear_model import LinearRegression
import numpy as np

def predict_future_price(product_id):
    """
    Uses simple linear regression on historical price data
    to predict if/when the price might hit a target or drop.
    """
    history = list(price_history_collection.find({"product_id": product_id}).sort("timestamp", 1))
    
    if len(history) < 5:
        return f"Prediction Model: Learning... (Needs at least 5 price checks to run the Regression ML algorithm. Currently has {len(history)} data points)"
        
    df = pd.DataFrame(history)
    if 'price' not in df.columns or 'timestamp' not in df.columns:
        return "Not enough data points."
        
    # Convert timestamps to numeric days since start
    start_time = df['timestamp'].min()
    df['days_since_start'] = (df['timestamp'] - start_time).dt.total_seconds() / (24 * 3600)
    
    # Train simple linear regression
    X = df[['days_since_start']].values
    y = df['price'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    trend = model.coef_[0] # price change per day
    
    if trend < -0.1: # Price is dropping
        return f"Prediction: The price is trending downwards (depositing about ₹{abs(trend):.2f}/day). A deal might be coming soon!"
    elif trend > 0.1: # Price is rising
        return f"Prediction: The price is currently trending upwards by approx. ₹{trend:.2f}/day. You might want to wait for the next sale."
    else:
        return "Prediction: The price seems to be relatively stable right now."

def get_product_trend_summary(product_id):
    history = list(price_history_collection.find({"product_id": product_id}).sort("timestamp", -1))
    if not history:
        return "No history available."
        
    current = history[0]['price']
    
    if len(history) == 1:
        return f"Tracking started at ₹{current}."
        
    stats_df = pd.DataFrame(history)
    lowest = stats_df['price'].min()
    highest = stats_df['price'].max()
    
    return f"Current: ₹{current} | Lowest Recorded: ₹{lowest} | Highest Recorded: ₹{highest}"
