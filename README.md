# Mashup Assignment

This repository contains the solution for the Mashup assignment, consisting of a CLI tool and a Web Service.

## Prerequisites

- Python 3.7+
- FFmpeg (installed and added to system PATH)

## Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Configuration (For Web App)

1.  Copy `.env.example` to `.env`.
2.  Fill in your SMTP credentials (required for email functionality).

    ```ini
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=587
    SMTP_USERNAME=your_email@gmail.com
    SMTP_PASSWORD=abcd-efgh-ijkl-mnop  # App Password, not login password
    SENDER_EMAIL=your_email@gmail.com
    ```

## Usage

### Program 1: Console App (CLI)

Run the script from the command line:

```bash
python 102303052.py <SingerName> <NumberOfVideos> <AudioDuration> <OutputFileName>
```

**Example:**
```bash
python 102303052.py "Sharry Maan" 20 20 101556-output.mp3
```

- **SingerName**: Name of the singer to search.
- **NumberOfVideos**: Number of videos to download (>10).
- **AudioDuration**: Duration of each clip in seconds (>20).
- **OutputFileName**: Output MP3 file name.

### Program 2: Web Service

1.  Start the Flask app:
    ```bash
    python app.py
    ```
2.  Open your browser and navigate to `http://127.0.0.1:5000`.
3.  Fill in the form and submit.
4.  The process runs in the background. You will receive an email with the ZIP file once completed.

## Hosting on Render.com (Recommended)

I have included a `render.yaml` file to make deployment automatic.

1.  **Push to GitHub**:
    - Create a new repository on GitHub.
    - Push all files in this folder to that repository.
    
    ```bash
    git init
    git add .
    git commit -m "Initial commit"
    git branch -M main
    git remote add origin <your-repo-url>
    git push -u origin main
    ```

2.  **Deploy on Render**:
    - Sign up/Login to [Render.com](https://render.com/).
    - Click **New +** and select **Blueprint**.
    - Connect your GitHub account and select the repository you just created.
    - Render will automatically detect the `render.yaml` file.
    - Click **Apply**.

3.  **Configure Environment Variables**:
    - In the Render dashboard for your new service, go to the **Environment** tab.
    - You must manually enter the values for:
        - `SMTP_USERNAME` (Your email)
        - `SMTP_PASSWORD` (Your App Password)
        - `SENDER_EMAIL` (Your email)
        - `SMTP_HOST` (smtp.gmail.com)
    - The other variables are already set by the blueprint, but double-check them.

4.  **Done!**: Your app will be live at `https://<service-name>.onrender.com`.

## Hosting on Vercel

> [!WARNING]
> **Timeout Limitations**: Vercel Serverless Functions have a default timeout of 10 seconds (up to 60s on Pro). Downloading and processing 10+ videos takes longer than this. The request might time out before the background thread completes, or the thread might be killed when the response is sent. **Render is highly recommended for this assignment.**

If you still want to deploy to Vercel:

1.  **Push to GitHub** (same steps as above).
2.  **Deploy on Vercel**:
    - Sign up at [https://vercel.com](https://vercel.com).
    - Import your GitHub repository.
    - Vercel will detect `vercel.json`.
3.  **Environment Variables**:
    - In the project settings on Vercel, go to **Settings > Environment Variables**.
    - Add `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SENDER_EMAIL` individually.
4.  **Deploy**.

## License
MIT
