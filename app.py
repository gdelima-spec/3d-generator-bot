from flask import Flask, render_template, request, jsonify, send_file
import openai
import trimesh
import tempfile
import requests
import base64
import os

app = Flask(__name__)

openai.api_key = os.environ.get("OPENAI_API_KEY")

stl_file_path = None

def generate_stl(prompt):
    size = max(5, min(len(prompt), 30))
    mesh = trimesh.creation.box(extents=(size, size/2, size/3))

    path = tempfile.NamedTemporaryFile(delete=False, suffix=".stl").name
    mesh.export(path)
    return path

def generate_text(prompt):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": f"Create a viral 3D printable model title and description for: {prompt}"
        }]
    )

    text = response["choices"][0]["message"]["content"]
    return "Generated Model", text

def generate_images(prompt):
    images = []

    img_prompt = f"Realistic 3D printed {prompt}, studio lighting, PLA plastic"

    for _ in range(2):
        result = openai.Image.create(
            prompt=img_prompt,
            n=1,
            size="512x512"
        )

        url = result["data"][0]["url"]
        img_data = requests.get(url).content
        images.append(base64.b64encode(img_data).decode())

    return images

@app.route("/")
def home():
    return "Server is running"

@app.route("/generate", methods=["POST"])
def generate():
    global stl_file_path

    prompt = request.json.get("prompt")

    stl_file_path = generate_stl(prompt)
    title, description = generate_text(prompt)
    images = generate_images(prompt)

    return jsonify({
        "title": title,
        "description": description,
        "images": images
    })

@app.route("/download")
def download():
    return send_file(stl_file_path, as_attachment=True)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)