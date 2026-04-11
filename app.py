from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import openai
import trimesh
import tempfile
import requests
import base64
import os

app = Flask(__name__)
CORS(app)

openai.api_key = os.environ.get("OPENAI_API_KEY")

stl_file_path = None

@app.route("/")
def home():
    return render_template("index.html")

def generate_stl(prompt):
    size = max(5, min(len(prompt), 30))
    mesh = trimesh.creation.box(extents=(size, size/2, size/3))
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".stl").name
    mesh.export(path)
    return path

def generate_text(prompt):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user", 
                "content": f"""Create a Printables-style listing.

User idea: {prompt}

Return EXACTLY in this format:
Title: [short catchy title, max 8 words]
Description: [detailed, SEO friendly description, 3-5 sentences]"""
            }]
        )
        text = response.choices[0].message.content.strip()
        
        # Better parsing
        if "Title:" in text and "Description:" in text:
            title = text.split("Title:")[1].split("Description:")[0].strip()
            description = text.split("Description:")[1].strip()
        else:
            title = prompt[:60].title() + " - 3D Printable Model"
            description = text[:800]
            
        return title, description
    except Exception as e:
        return "Cool 3D Printable Model", "Failed to generate description. Try again."

def generate_images(prompt):
    images = []
    img_prompt = f"Professional product photography of a highly detailed 3D printed {prompt}, realistic PLA plastic texture, studio lighting, clean white background, high resolution"

    for _ in range(2):
        try:
            result = openai.images.generate(
                model="dall-e-3",
                prompt=img_prompt,
                n=1,
                size="512x512"
            )
            url = result.data[0].url
            img_data = requests.get(url).content
            images.append(base64.b64encode(img_data).decode('utf-8'))
        except Exception as e:
            print("Image generation failed:", str(e))
            images.append("")  # empty = will show placeholder
    return images

@app.route("/generate", methods=["POST"])
def generate():
    global stl_file_path
    data = request.get_json()
    prompt = data.get("prompt", "cool gadget")

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
    if not stl_file_path:
        return "No model generated yet", 404
    return send_file(stl_file_path, as_attachment=True, download_name="model.stl")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
