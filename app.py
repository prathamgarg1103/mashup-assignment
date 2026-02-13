import os
import shutil
import smtplib
import subprocess
import sys
import tempfile
import zipfile
from email.message import EmailMessage
from pathlib import Path
from typing import Tuple

from email_validator import EmailNotValidError, validate_email
from flask import Flask, render_template_string, request

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
CLI_SCRIPT = BASE_DIR / "102303052.py"

FORM_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mashup Service</title>
  <style>
    body {
      margin: 0;
      font-family: Arial, sans-serif;
      background: #f1f5f9;
      color: #0f172a;
    }
    .container {
      max-width: 720px;
      margin: 40px auto;
      background: white;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(2, 6, 23, 0.08);
      padding: 28px;
    }
    h1 {
      margin-top: 0;
      font-size: 26px;
    }
    p.note {
      margin-top: 0;
      font-size: 14px;
      color: #334155;
    }
    label {
      display: block;
      margin-top: 16px;
      margin-bottom: 6px;
      font-weight: 700;
    }
    input {
      width: 100%;
      box-sizing: border-box;
      padding: 10px;
      border: 1px solid #cbd5e1;
      border-radius: 8px;
      font-size: 14px;
    }
    button {
      margin-top: 18px;
      width: 100%;
      border: 0;
      border-radius: 8px;
      background: #0ea5e9;
      color: white;
      padding: 12px;
      font-size: 15px;
      font-weight: 700;
      cursor: pointer;
    }
    .msg {
      margin-top: 16px;
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 14px;
    }
    .msg.success {
      background: #dcfce7;
      color: #166534;
      border: 1px solid #86efac;
    }
    .msg.error {
      background: #fee2e2;
      color: #991b1b;
      border: 1px solid #fca5a5;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Mashup Assignment - Program 2</h1>
    <p class="note">Enter singer, video count, clip duration, and destination email. A ZIP file will be mailed after generation.</p>
    <form method="post">
      <label for="singer_name">Singer Name</label>
      <input id="singer_name" name="singer_name" value="{{ values.singer_name }}" required>

      <label for="number_of_videos">Number of Videos (must be > 10)</label>
      <input id="number_of_videos" name="number_of_videos" type="number" min="11" value="{{ values.number_of_videos }}" required>

      <label for="audio_duration">Duration of Each Clip in Seconds (must be > 20)</label>
      <input id="audio_duration" name="audio_duration" type="number" min="21" value="{{ values.audio_duration }}" required>

      <label for="email">Email ID</label>
      <input id="email" name="email" type="email" value="{{ values.email }}" required>

      <button type="submit">Create and Email Mashup</button>
    </form>
    {% if message %}
      <div class="msg {{ status }}">{{ message }}</div>
    {% endif %}
  </div>
</body>
</html>
"""


def parse_form(form) -> Tuple[str, int, int, str]:
    singer_name = form.get("singer_name", "").strip()
    if not singer_name:
        raise ValueError("Singer name is required.")

    try:
        number_of_videos = int(form.get("number_of_videos", "").strip())
    except ValueError:
        raise ValueError("Number of videos must be a valid integer.")
    if number_of_videos <= 10:
        raise ValueError("Number of videos must be greater than 10.")

    try:
        audio_duration = int(form.get("audio_duration", "").strip())
    except ValueError:
        raise ValueError("Audio duration must be a valid integer.")
    if audio_duration <= 20:
        raise ValueError("Audio duration must be greater than 20.")

    email_raw = form.get("email", "").strip()
    try:
        email = validate_email(email_raw, check_deliverability=False).normalized
    except EmailNotValidError:
        raise ValueError("Email ID is not valid.")

    return singer_name, number_of_videos, audio_duration, email


def create_zip_file(source_file: Path) -> Path:
    zip_path = source_file.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(source_file, arcname=source_file.name)
    return zip_path


def run_cli_mashup(singer_name: str, number_of_videos: int, audio_duration: int, output_file: Path) -> None:
    command = [
        sys.executable,
        str(CLI_SCRIPT),
        singer_name,
        str(number_of_videos),
        str(audio_duration),
        str(output_file),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "Unknown CLI failure."
        raise RuntimeError(f"Mashup generation failed: {details}")


def send_email_with_attachment(
    receiver_email: str,
    singer_name: str,
    number_of_videos: int,
    audio_duration: int,
    attachment_path: Path,
) -> None:
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender_email = os.getenv("SENDER_EMAIL", smtp_username or "")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in {"1", "true", "yes"}

    if not smtp_username or not smtp_password:
        raise RuntimeError(
            "SMTP credentials not configured. Set SMTP_USERNAME and SMTP_PASSWORD."
        )
    if not sender_email:
        raise RuntimeError("Sender email is missing. Set SENDER_EMAIL or SMTP_USERNAME.")

    message = EmailMessage()
    message["Subject"] = "Mashup Assignment Output"
    message["From"] = sender_email
    message["To"] = receiver_email
    message.set_content(
        "Your mashup file is attached.\n\n"
        f"Singer: {singer_name}\n"
        f"Videos: {number_of_videos}\n"
        f"Clip duration: {audio_duration} seconds\n"
    )

    with attachment_path.open("rb") as file_obj:
        data = file_obj.read()
    message.add_attachment(
        data,
        maintype="application",
        subtype="zip",
        filename=attachment_path.name,
    )

    with smtplib.SMTP(host=smtp_host, port=smtp_port, timeout=120) as smtp:
        if use_tls:
            smtp.starttls()
        smtp.login(smtp_username, smtp_password)
        smtp.send_message(message)


@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    status = "success"
    values = {
        "singer_name": "",
        "number_of_videos": "11",
        "audio_duration": "30",
        "email": "",
    }

    if request.method == "POST":
        values = {
            "singer_name": request.form.get("singer_name", ""),
            "number_of_videos": request.form.get("number_of_videos", ""),
            "audio_duration": request.form.get("audio_duration", ""),
            "email": request.form.get("email", ""),
        }
        temp_dir = Path(tempfile.mkdtemp(prefix="mashup_web_"))
        try:
            singer_name, number_of_videos, audio_duration, email = parse_form(request.form)
            output_mp3 = temp_dir / "mashup_output.mp3"
            run_cli_mashup(singer_name, number_of_videos, audio_duration, output_mp3)
            zip_file = create_zip_file(output_mp3)
            send_email_with_attachment(
                receiver_email=email,
                singer_name=singer_name,
                number_of_videos=number_of_videos,
                audio_duration=audio_duration,
                attachment_path=zip_file,
            )
            message = f"Success: mashup ZIP has been emailed to {email}."
            status = "success"
        except Exception as exc:
            message = f"Error: {exc}"
            status = "error"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    return render_template_string(FORM_HTML, message=message, status=status, values=values)


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"}
    app.run(host=host, port=port, debug=debug)
