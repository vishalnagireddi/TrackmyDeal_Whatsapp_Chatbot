# TrackMyDeal 🛒

TrackMyDeal is an advanced price-tracking WhatsApp chatbot that monitors products across major e-commerce platforms and sends real-time notifications directly to your phone. It uses web scraping to track prices and machine learning to predict price trends.

## 🚀 Features

- **Multi-Platform Support**: Automatically tracks prices from **Amazon**, **Flipkart**, **Myntra**, and **Nykaa**.
- **WhatsApp Integration**: Seamlessly interact with the bot through the Meta WhatsApp Cloud API.
- **Price Drop Alerts**: Get instant WhatsApp notifications when a tracked product hits a new historical low.
- **Visual Trend Analysis**: Generate and receive price trend graphs for any tracked item.
- **Smart Predictions**: Leverages machine learning to forecast future price movements.
- **Stealth Scraping**: Equipped with advanced bot detection bypass (Playwright stealth and TLS fingerprinting).
- **Daily Summaries**: Automatically sends a daily status report of all tracked products at 9:00 AM.
- **Background Automation**: Continuous 24/7 monitoring powered by APScheduler.

## 🛠️ Tech Stack

- **Backend**: Python, Flask
- **Database**: MongoDB (Atlas)
- **Scraping**: Playwright, BeautifulSoup, curl_cffi
- **Automation**: APScheduler, Threading
- **Data & Visualization**: Pandas, Scikit-learn, Matplotlib
- **Messaging**: Meta WhatsApp Cloud API

## 📋 Commands

Interact with the bot using these simple commands:

- **Send any link**: Send a product URL from Amazon, Flipkart, Myntra, or Nykaa to start tracking.
- `Hi` / `Hello`: Start a conversation and get a brief introduction.
- `Products` / `List`: View all products you are currently tracking.
- `Exit [number]`: Stop tracking a specific product (e.g., `exit 2`).
- `Yes` / `Ok` (after listing products): Check for detailed price drop information since you started tracking.

## ⚙️ Getting Started

### Prerequisites

- Python 3.10 or higher
- MongoDB Atlas account (or local MongoDB instance)
- Meta WhatsApp Cloud API setup (Access Token, Phone Number ID)

### Setup Instructions

1.  **Clone the Repository**:
    ```bash
    git clone <repository_url>
    cd TrackmyDeal
    ```

2.  **Create a Virtual Environment**:
    ```bash
    python -m venv venv
    ./venv/Scripts/activate  # On Windows
    # source venv/bin/activate  # On Linux/macOS
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    playwright install chromium
    ```

4.  **Configure Environment Variables**:
    Create a `.env` file in the root directory and add the following:
    ```env
    MONGO_URI=your_mongodb_uri
    META_WHATSAPP_TOKEN=your_meta_access_token
    META_PHONE_NUMBER_ID=your_phone_number_id
    META_VERIFY_TOKEN=your_webhook_verify_token
    PORT=5000
    ```

5.  **Run the Application**:
    ```bash
    python app.py
    ```

## 🚀 Deployment

The project is designed to be easily deployed on **Render.com**. Use the provided `render.yaml` and `build.sh` for a seamless setup.

- **Build Command**: `./build.sh`
- **Start Command**: `gunicorn app:app`

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request or open an issue.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
