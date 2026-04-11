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
    # Better STL - more interesting shape
    seed = hash(prompt) % 8
    if seed < 3:
        # Box with something on top
        base = trimesh.creation.box(extents=(30, 20, 8))
        top = trimesh.creation.box(extents=(18, 12, 10))
        top.apply_translation([0, 0, 9])
        mesh = trimesh.util.concatenate([base, top])
    else:
        mesh = trimesh.creation.icosphere(radius=15, subdivisions=2)
        base = trimesh.creation.box(extents=(35, 35, 6))
        mesh = trimesh.util.concatenate([mesh, base])
    
    path = tempfile.NamedTemporaryFile(delete=False, suffix=".stl").name
    mesh.export(path)
    return path

def generate_text(prompt):
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"Create a good Printables.com style listing for a 3D model of: {prompt}\n\nReturn exactly:\nTitle: [short catchy title]\nDescription: [nice 4-6 sentence description]"
            }]
        )
        text = response.choices[0].message.content.strip()
        
        if "Title:" in text and "Description:" in text:
            title = text.split("Title:")[1].split("Description:")[0].strip()
            description = text.split("Description:")[1].strip()
        else:
            title = f"{prompt.title()} 3D Printable Model"
            description = text
        return title, description
    except:
        return f"{prompt.title()} 3D Model", "High quality 3D printable model."

def generate_images(prompt):
    images = []
    img_prompt = f"realistic product photo of a 3D printed {prompt}, made with colorful PLA filament, on a clean desk with soft lighting, professional photography, sharp focus"

    for _ in range(2):
        try:
            result = openai.images.generate(
                model="dall-e-2",   # dall-e-2 is more reliable for this
                prompt=img_prompt,
                n=1,
                size="512x512"
            )
            url = result.data[0].url
            img_data = requests.get(url).content
            images.append(base64.b64encode(img_data).decode('utf-8'))
        except Exception as e:
            print("Image error:", str(e))
            images.append("")  
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
        return "No model yet", 404
    return send_file(stl_file_path, as_attachment=True, download_name="model.stl")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
