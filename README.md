# 🎵 Mashup Assignment

A robust Python application that creates a mashup of songs from a specific singer by downloading videos from YouTube, trimming them, and merging them into a single audio file. This project includes both a **Command Line Interface (CLI)** and a **Web Service**.

![Python](https://img.shields.io/badge/Python-3.7%2B-blue)
![Flask](https://img.shields.io/badge/Flask-2.0%2B-green)
![Status](https://img.shields.io/badge/Status-Completed-success)

## ✨ Features

- **Download & Process**: Automatically downloads N videos of a singer from YouTube.
- **Audio Processing**: Extracts audio, trims to Y seconds, and merges them.
- **Background Processing**: Web app handles long-running tasks asynchronously to prevent timeouts.
- **Email Delivery**: Sends the final mashup (zipped) directly to your email.
- **Robust Error Handling**: Retries downloads and handles API failures gracefully.
- **Deployment Ready**: Configured for **Render** (recommended) and Vercel.

---

## 🚀 Quick Start (Local)

### Prerequisites
- Python 3.7+
- FFmpeg (must be added to system PATH)

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/prathamgarg1103/mashup-assignment.git
    cd mashup-assignment
    ```

2.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Environment Setup**:
    Create a `.env` file (copy from `.env.example`) and add your SMTP credentials:
    ```ini
    SMTP_USERNAME=your_email@gmail.com
    SMTP_PASSWORD=abcd-efgh-ijkl-mnop  # Google App Password
    SENDER_EMAIL=your_email@gmail.com
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    ```

### Usage

#### Option 1: CLI Tool
Run the script directly from your terminal:
```bash
# Syntax: python 102303052.py <Singer> <Count> <Duration> <OutputParams>
python 102303052.py "Arijit Singh" 20 30 output.mp3
```

#### Option 2: Web App
Start the Flask server:
```bash
python app.py
```
Visit `http://localhost:5000` in your browser.

---

## 🌐 Deployment

### ✅ Method 1: Render (Highly Recommended)
Render supports long-running background tasks, which are essential for processing video mashups.

1.  **Fork/Clone** this repo to your GitHub.
2.  Sign up on [Render.com](https://render.com).
3.  Click **New +** -> **Blueprint**.
4.  Connect your repository.
5.  Render will auto-detect the `render.yaml` configuration. Click **Apply**.
6.  **Important**: Go to the **Environment** tab of your new service and add these variables:
    - `SMTP_USERNAME`: (Your Email)
    - `SMTP_PASSWORD`: (Your App Password)
    - `SENDER_EMAIL`: (Your Email)
    - `SMTP_HOST`: `smtp.gmail.com`
    - `SMTP_PORT`: `587`

### ⚠️ Method 2: Vercel
**Note**: Vercel has a 10s timeout for serverless functions. This app may fail to process large mashups on Vercel.

1.  Import project to Vercel.
2.  Add the same Environment Variables in Project Settings.
3.  Deploy.

---

## 🛠 Troubleshooting

- **Email not received?**
    - Check your Spam folder.
    - Verify your `SMTP_PASSWORD` is a valid Google App Password, not your login password.
    - Use the debug route `/test-email` on your deployed app to test credentials instantly.
- **Processing fails?**
    - Ensure `ffmpeg` is installed correctly locally.
    - On Render, this is handled automatically by the environment.

## 📜 License
MIT
