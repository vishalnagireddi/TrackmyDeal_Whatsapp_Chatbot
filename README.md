# TrackMyDeal 🛒

TrackMyDeal is a powerful price tracking bot that monitors products on major e-commerce platforms and sends notifications directly via WhatsApp.

## 🚀 Features

- **Multi-Platform Support**: Scrapes prices from Amazon, Flipkart, Myntra, and Nykaa.
- **WhatsApp Integration**: Interact with the bot directly via WhatsApp.
- **Price Drop Alerts**: Receive instant notifications whenever a tracked product hits a new historical low.
- **Daily Summaries**: Get a daily digest at 9:00 AM status of all your tracked products, including trend graphs.
- **Smart Predictions**: Uses machine learning to predict future price trends based on historical data.
- **Bot Detection Bypass**: Utilizes advanced stealth measures (`playwright-stealth` and TLS fingerprinting) to ensure reliable scraping.

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **Database**: MongoDB
- **Scraping**: Playwright, curl_cffi, BeautifulSoup
- **Automation**: APScheduler
- **Data Science**: Pandas, Scikit-learn, Matplotlib
- **Messaging**: Meta WhatsApp Cloud API

## 📋 Commands

- `Hi` / `Hello`: Start a conversation or add a new link.
- `products` / `list`: View all products you are currently tracking.
- `exit [number]`: Stop tracking a specific product.
- `graph [number]`: Generate a price trend graph for a specific product.

## ⚙️ How it Works

1. **Monitoring**: The system tracks prices for all products every 3 hours.
2. **Alerting**: If a price drop is detected, an alert is sent immediately.
3. **Daily Digest**: Every morning at 9:00 AM, a summary of all tracked items is sent with their latest trend graphs.
