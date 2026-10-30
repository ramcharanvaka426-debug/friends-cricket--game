from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

players = {}
connections = []

@app.get("/")
def home():
    return {
        "message": "Friends Cricket Game Server is Running!"
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
                    try:
                        await connection.send_text(message)
                    except:
                        connections.remove(connection)

    except WebSocketDisconnect:
        if websocket in connections:
            connections.remove(websocket)
