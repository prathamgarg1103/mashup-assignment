# Mashup Assignment

This repo includes complete implementations for:

- Program 1: Command-line mashup generator (`102303052.py`)
- Program 2: Flask web service (`app.py`) that emails the mashup ZIP

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Program 1 (CLI)

Usage:

```bash
python 102303052.py <SingerName> <NumberOfVideos> <AudioDuration> <OutputFileName>
```

Example:

```bash
python 102303052.py "Sharry Maan" 20 30 mashup.mp3
```

Input rules:

- `NumberOfVideos` must be greater than 10.
- `AudioDuration` must be greater than 20.
- `OutputFileName` must end with `.mp3`.

What it does:

1. Downloads N YouTube videos for the singer.
2. Extracts audio and trims first Y seconds from each.
3. Merges all snippets into a single MP3 output.

## Program 2 (Web Service)

Run:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

Form fields:

- Singer name
- Number of videos
- Duration of each clip
- Email ID

The service generates mashup audio, zips it, and sends it by email.

### SMTP Configuration (Required for email sending)

Set these environment variables before running `app.py`:

- `SMTP_USERNAME` (your SMTP login/email)
- `SMTP_PASSWORD` (SMTP password or app password)

Optional:

- `SMTP_HOST` (default: `smtp.gmail.com`)
- `SMTP_PORT` (default: `587`)
- `SMTP_USE_TLS` (default: `true`)
- `SENDER_EMAIL` (default: value of `SMTP_USERNAME`)

PowerShell example:

```powershell
$env:SMTP_USERNAME="your_email@gmail.com"
$env:SMTP_PASSWORD="your_app_password"
python app.py
```
