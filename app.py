from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
load_dotenv()
from generate_post import generate_post
from generate_youtube_desc import generate_youtube_description

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Input text is empty"}), 400
    try:
        post = generate_post(text)
        return jsonify({"post": post})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/generate-youtube", methods=["POST"])
def generate_youtube():
    data = request.get_json(silent=True) or {}
    title   = data.get("title", "").strip()
    context = data.get("context", "").strip()
    if not title:
        return jsonify({"error": "Video title is empty"}), 400
    try:
        desc = generate_youtube_description(title, context)
        return jsonify({"description": desc})
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=5000)
