from flask import Flask, render_template_string, request

app = Flask(__name__)

FORM_HTML = """
<!doctype html>
<html>
<head><title>Mashup Service</title></head>
<body>
  <h2>Mashup Assignment - Program 2</h2>
  <form method="post">
    <label>Singer Name:</label><br>
    <input name="singer_name" required><br><br>

    <label># of videos:</label><br>
    <input name="number_of_videos" type="number" min="11" required><br><br>

    <label>Duration of each video (sec):</label><br>
    <input name="audio_duration" type="number" min="21" required><br><br>

    <label>Email:</label><br>
    <input name="email" type="email" required><br><br>

    <button type="submit">Submit</button>
  </form>
  <p>{{ message }}</p>
</body>
</html>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    if request.method == "POST":
        # TODO: Trigger mashup creation and send zip to email.
        message = "Request received. Implement backend workflow for generation and email delivery."
    return render_template_string(FORM_HTML, message=message)


if __name__ == "__main__":
    app.run(debug=True)