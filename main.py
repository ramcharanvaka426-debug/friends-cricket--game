from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

players = []
connections = []

@app.get("/")
def home():
    return {
        "message": "Friends Cricket Game Server is Running!"
    }

@app.post("/register")
def register(player: dict):
    if len(players) >= 11:
        return {"message": "Team is full!"}

    players.append(player)

    return {
        "message": "Player registered successfully!",
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
