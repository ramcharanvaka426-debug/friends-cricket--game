from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse

app = FastAPI()

players = []
connections = []

@app.get("/")
def home():
    return FileResponse("index.html")

@app.post("/register")
def register(player: dict):
    if len(players) >= 11:
        return {"message": "Team is full!"}

    players.append(player)

    return {
        "message": "Registration successful!",
        "players": players
    }

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
