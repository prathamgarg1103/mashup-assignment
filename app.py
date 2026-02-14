import os
import shutil
import smtplib
import subprocess
import sys
import tempfile
import threading
import zipfile
from email.message import EmailMessage
from pathlib import Path
from typing import Tuple

from email_validator import EmailNotValidError, validate_email
from flask import Flask, render_template_string, request, send_from_directory
import time

# Try to load .env file if python-dotenv is installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
    .msg.info {
        background: #e0f2fe;
        color: #0369a1;
        border: 1px solid #7dd3fc;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Mashup Assignment - Program 2</h1>
    <p class="note">Enter singer, video count, clip duration, and destination email. A ZIP file will be mailed after generation. <strong>Processing happens in the background.</strong></p>
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
    # Ensure CLI script exists
    if not CLI_SCRIPT.exists():
         raise RuntimeError(f"CLI script not found at {CLI_SCRIPT}")

    command = [
        sys.executable,
        str(CLI_SCRIPT),
        singer_name,
        str(number_of_videos),
        str(audio_duration),
        str(output_file),
    ]
    # Capture output for debugging logs if needed
    print(f"Starting CLI command: {' '.join(command)}")
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    
    if completed.returncode != 0:
        details = completed.stderr.strip() or completed.stdout.strip() or "Unknown CLI failure."
        print(f"CLI Error: {details}")
        raise RuntimeError(f"Mashup generation failed: {details}")
    print(f"CLI completed successfully: {output_file}")


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
        print("Error: SMTP credentials missing. Cannot send email.")
        return # Cannot send email, but logged error.

    if not sender_email:
        print("Error: SENDER_EMAIL missing.")
        return

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

    try:
        with attachment_path.open("rb") as file_obj:
            data = file_obj.read()
        message.add_attachment(
            data,
            maintype="application",
            subtype="zip",
            filename=attachment_path.name,
        )

        print(f"Sending email to {receiver_email}...")
        with smtplib.SMTP(host=smtp_host, port=smtp_port, timeout=120) as smtp:
            if use_tls:
                smtp.starttls()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")


# Global directory for results (persists as long as app runs)
STATIC_RESULTS_DIR = Path("static_results")
STATIC_RESULTS_DIR.mkdir(exist_ok=True)

def update_status(file_id, status, message=""):
    """Write status to a file for the frontend to poll."""
    status_file = STATIC_RESULTS_DIR / f"{file_id}.txt"
    with open(status_file, "w") as f:
        f.write(f"{status}|{message}")

def process_mashup_request(singer_name, number_of_videos, audio_duration, email, file_id):
    """Background task to run mashup and email result."""
    temp_dir = Path(tempfile.mkdtemp(prefix="mashup_web_"))
    update_status(file_id, "Processing", "Starting download and processing...")
    
    try:
        print(f"Processing request for {email} / {singer_name}")
        
        # We generate a .mp4 for the preview
        output_file = temp_dir / file_id
        
        run_cli_mashup(singer_name, number_of_videos, audio_duration, output_file)
        
        if output_file.exists():
            update_status(file_id, "Processing", "Creating zip and sending email...")
            # 1. Create ZIP for email
            zip_file = create_zip_file(output_file)
            send_email_with_attachment(
                receiver_email=email,
                singer_name=singer_name,
                number_of_videos=number_of_videos,
                audio_duration=audio_duration,
                attachment_path=zip_file,
            )
            
            # 2. Move MP4 to static folder for preview
            shutil.move(str(output_file), str(STATIC_RESULTS_DIR / file_id))
            print(f"Video available at {STATIC_RESULTS_DIR / file_id}")
            update_status(file_id, "Done", "Mashup created and emailed successfully!")
            
        else:
             print("Error: Output file was not created by CLI.")
             update_status(file_id, "Failed", "Output file was not created by CLI logic.")

    except Exception as exc:
        print(f"Background processing error: {exc}")
        update_status(file_id, "Failed", str(exc))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@app.route("/result/<filename>")
def result(filename):
    """Serve the result page with video player and status."""
    if "/" in filename or "\\" in filename:
        return "Invalid filename", 400
    
    status_file = STATIC_RESULTS_DIR / f"{filename}.txt"
    current_status = "Processing"
    details = "Waiting for update..."

    if status_file.exists():
        try:
            with open(status_file, "r") as f:
                content = f.read().strip().split("|", 1)
                current_status = content[0]
                if len(content) > 1:
                    details = content[1]
        except:
            pass
            
    # Auto-refresh meta tag if processing
    refresh_tag = '<meta http-equiv="refresh" content="5">' if current_status == "Processing" else ""

    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      {{ refresh_tag|safe }}
      <title>Mashup Status</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f1f5f9; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); text-align: center; max-width: 800px; width: 90%; }
        h1 { color: #0f172a; margin-bottom: 20px; }
        .status { font-size: 18px; margin-bottom: 20px; font-weight: bold; }
        .Processing { color: #d97706; }
        .Failed { color: #dc2626; }
        .Done { color: #16a34a; }
        video { width: 100%; border-radius: 8px; margin-top: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .btn { display: inline-block; margin-top: 20px; padding: 12px 24px; background: #0ea5e9; color: white; text-decoration: none; border-radius: 6px; font-weight: bold; }
        .btn:hover { background: #0284c7; }
        pre { background: #fee2e2; padding: 10px; border-radius: 6px; overflow-x: auto; text-align: left; }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>Mashup Status</h1>
        
        <div class="status {{ status }}">Status: {{ status }}</div>
        <p>{{ details }}</p>

        {% if status == 'Done' %}
            <video controls autoplay>
                <source src="/download/{{ filename }}" type="video/mp4">
                Your browser does not support the video tag.
            </video>
        {% elif status == 'Failed' %}
            <p>Something went wrong. Please check the error above.</p>
        {% else %}
            <p>Please wait...</p>
            <div style="margin: 20px auto; border: 4px solid #f3f3f3; border-top: 4px solid #3498db; border-radius: 50%; width: 30px; height: 30px; animation: spin 2s linear infinite;"></div>
            <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
        {% endif %}

        <br>
        <a href="/" class="btn">Back to Home</a>
      </div>
    </body>
    </html>
    """, filename=filename, status=current_status, details=details, refresh_tag=refresh_tag)

@app.route("/download/<path:filename>")
def download_file(filename):
    """Serve the generated video file."""
    return send_from_directory(STATIC_RESULTS_DIR, filename)

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
        
        try:
            singer_name, number_of_videos, audio_duration, email = parse_form(request.form)
            
            # Generate ID for video
            file_id = f"{int(time.time())}_{abs(hash(singer_name))}.mp4"
            
            # Start background thread
            thread = threading.Thread(
                target=process_mashup_request,
                args=(singer_name, number_of_videos, audio_duration, email, file_id),
                daemon=True
            )
            thread.start()
            
            message = (
                f"Request initiated for singer '{singer_name}'. "
                f"We are creating a <strong>video preview</strong> and emailing the zip. "
                f"<br><br>👉 <strong><a href='/result/{file_id}'>Click here to watch the Video Preview</a></strong> "
                f"(Please wait ~1 minute for generation)."
            )
            status = "info"
        except ValueError as exc:
            message = f"Input Error: {exc}"
            status = "error"
        except Exception as exc:
            message = f"System Error: {exc}"
            status = "error"

    return render_template_string(FORM_HTML, message=message, status=status, values=values)


@app.route("/test-email", methods=["GET", "POST"])
def test_email_route():
    """Debug route to verify SMTP credentials instantly."""
    if request.method == "POST":
        email = request.form.get("email")
        try:
             # Create a dummy file to reuse the existing function
             with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
                 tmp.write(b"This is a test email to verify credentials.")
                 tmp_path = Path(tmp.name)
                 tmp.close() # Ensure checks are flushed
             
             try:
                 # Sending dummy file
                 send_email_with_attachment(email, "TEST_SINGER", 1, 1, tmp_path)
                 return f"Email sent successfully to {email}! Credentials work."
             finally:
                 if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        except Exception as e:
            return f"Failed to send email: {e}"
            
    return """
    <h2>Test Email Configuration</h2>
    <form method="post">
        <label>Enter Email to Test:</label>
        <input name="email" type="email" required placeholder="your.email@example.com" style="padding: 10px; width: 300px;">
        <button type="submit" style="padding: 10px;">Test Now</button>
    </form>
    """


if __name__ == "__main__":
    host = os.getenv("FLASK_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_PORT", "5000"))
    debug = os.getenv("FLASK_DEBUG", "false").lower() in {"1", "true", "yes"}
    print(f"Starting Flask app on {host}:{port}")
    app.run(host=host, port=port, debug=debug)
