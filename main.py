
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import HTTPException
import os
import uuid

app = FastAPI()

os.makedirs("uploads", exist_ok=True)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

players = []
connections = []


# MAIN REGISTRATION PAGE
@app.get("/")
def home():
    return FileResponse("index.html")


# CRICKET GAME PAGE
@app.get("/game.html")
def game_page():
    if not os.path.isfile("game.html"):
        raise HTTPException(status_code=404, detail="game.html file not found")
    return FileResponse("game.html")


# REGISTER PLAYER
@app.post("/register")
async def register(
    name: str = Form(...),
    photo: UploadFile = File(...)
):
    if len(players) >= 11:
        return {"message": "Team is full!"}

    if not name.strip():
        return {"message": "Please enter your name!"}

    if not photo.content_type or not photo.content_type.startswith("image/"):
        return {"message": "Please upload an image!"}

    extension = os.path.splitext(photo.filename)[1].lower()

    if extension not in [".jpg", ".jpeg", ".png", ".webp"]:
        return {"message": "Use JPG, PNG or WEBP photos."}

    image_data = await photo.read(5 * 1024 * 1024 + 1)

    if len(image_data) > 5 * 1024 * 1024:
        return {"message": "Photo must be smaller than 5 MB."}

    filename = str(uuid.uuid4()) + extension
    filepath = os.path.join("uploads", filename)

    with open(filepath, "wb") as f:
        f.write(image_data)

    player = {
        "name": name.strip(),
        "photo": "/uploads/" + filename,
        "type": "Human"
    }

    players.append(player)

    return {
        "message": "Registration successful!",
        "player": player,
        "total_players": len(players)
    }


# DISPLAY PLAYERS
@app.get("/players")
def get_players():
    return {
        "total_players": len(players),
        "players": players
    }


# WEBSOCKET CONNECTION
@app.websocket("/ws")
async def game_connection(websocket: WebSocket):
    await websocket.accept()
    connections.append(websocket)

    try:
        while True:
            message = await websocket.receive_text()

            for connection in connections[:]:
                if connection != websocket:
                    await connection.send_text(message)

    except WebSocketDisconnect:
        if websocket in connections:
            connections.remove(websocket)
