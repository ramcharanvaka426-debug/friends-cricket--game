
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
import uuid

app = FastAPI()

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

players = []
connections = []

# CRICKET MATCH SETTINGS
OVERS_PER_INNINGS = 10
WICKETS_PER_INNINGS = 10

match = {
    "started": False,
    "finished": False,
    "innings": 1,
    "batting_team": "Team A",
    "overs": 0,
    "balls": 0,
    "runs": 0,
    "wickets": 0,
    "extras": 0,
    "history": [],
    "team_a_score": 0,
    "team_b_score": 0,
    "result": "Match not started"
}


def reset_innings():
    match["overs"] = 0
    match["balls"] = 0
    match["runs"] = 0
    match["wickets"] = 0
    match["extras"] = 0
    match["history"] = []


def innings_finished():
    return (
        match["overs"] >= OVERS_PER_INNINGS
        or match["wickets"] >= WICKETS_PER_INNINGS
    )


def update_team_score():
    if match["batting_team"] == "Team A":
        match["team_a_score"] = match["runs"]
    else:
        match["team_b_score"] = match["runs"]


def finish_innings():
    update_team_score()

    if match["innings"] == 1:
        match["innings"] = 2
        match["batting_team"] = "Team B"
        reset_innings()
        match["result"] = "Second innings started"
    else:
        match["finished"] = True

        if match["team_a_score"] > match["team_b_score"]:
            match["result"] = "Team A wins!"
        elif match["team_b_score"] > match["team_a_score"]:
            match["result"] = "Team B wins!"
        else:
            match["result"] = "Match tied!"


# MAIN PAGE
@app.get("/")
def home():
    return FileResponse("index.html")


# CRICKET GROUND
@app.get("/game.html")
def game_page():
    if not os.path.isfile("game.html"):
        raise HTTPException(status_code=404, detail="Game page not found")
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
        raise HTTPException(status_code=400, detail="Enter your name")

    if not photo.content_type or not photo.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Upload an image")

    extension = os.path.splitext(photo.filename)[1].lower()

    if extension not in [".jpg", ".jpeg", ".png", ".webp"]:
        raise HTTPException(status_code=400, detail="Use JPG, PNG or WEBP")

    image_data = await photo.read(5 * 1024 * 1024 + 1)

    if len(image_data) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Photo must be under 5 MB")

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


# START A NEW MATCH
@app.post("/match/new")
def new_match():
    match.update({
        "started": True,
        "finished": False,
        "innings": 1,
        "batting_team": "Team A",
        "team_a_score": 0,
        "team_b_score": 0,
        "result": "Team A batting first"
    })

    reset_innings()
    return match


# BALL INPUT
class BallInput(BaseModel):
    kind: str = "runs"
    runs: int = 0


@app.post("/match/ball")
def play_ball(ball: BallInput):

    if not match["started"]:
        raise HTTPException(status_code=400, detail="Start a match first")

    if match["finished"]:
        raise HTTPException(status_code=400, detail="Match is finished")

    if ball.kind not in [
        "runs", "wicket", "wide", "no_ball", "bye", "leg_bye"
    ]:
        raise HTTPException(status_code=400, detail="Invalid ball type")

    if ball.runs not in [0, 1, 2, 3, 4, 6]:
        raise HTTPException(status_code=400, detail="Runs must be 0, 1, 2, 3, 4 or 6")

    legal_ball = True
    total_runs = ball.runs
    description = ""

    if ball.kind == "runs":
        description = str(ball.runs) + " runs"

    elif ball.kind == "wicket":
        if match["wickets"] >= WICKETS_PER_INNINGS:
            raise HTTPException(status_code=400, detail="All wickets are down")
        match["wickets"] += 1
        total_runs = 0
        description = "WICKET!"

    elif ball.kind == "wide":
        total_runs = 1 + ball.runs
        match["extras"] += 1
        legal_ball = False
        description = "Wide ball"

    elif ball.kind == "no_ball":
        total_runs = 1 + ball.runs
        match["extras"] += 1
        legal_ball = False
        description = "No ball"

    elif ball.kind == "bye":
        match["extras"] += ball.runs
        description = str(ball.runs) + " byes"

    elif ball.kind == "leg_bye":
        match["extras"] += ball.runs
        description = str(ball.runs) + " leg byes"

    match["runs"] += total_runs

    if legal_ball:
        match["balls"] += 1

        if match["balls"] == 6:
            match["overs"] += 1
            match["balls"] = 0

    match["history"].append({
        "ball": str(match["overs"]) + "." + str(match["balls"]),
        "description": description,
        "runs": total_runs,
        "wickets": match["wickets"]
    })

    update_team_score()

    # Check innings end
    if innings_finished():
        finish_innings()

    return match


# VIEW CURRENT MATCH
@app.get("/match")
def get_match():
    return {
        "overs_per_innings": OVERS_PER_INNINGS,
        "match": match
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
                    try:
                        await connection.send_text(message)
                    except Exception:
                        connections.remove(connection)

    except WebSocketDisconnect:
        if websocket in connections:
            connections.remove(websocket)
