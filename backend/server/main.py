from typing import Annotated

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from core.board.detector import BoardDetector

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/fen")
def get_fen(board_file: Annotated[UploadFile, File()]):
def get_fen(board_file: UploadFile = File(...)):
    board_image = Image.open(board_file.file)
    board_detector = BoardDetector()
    board = board_detector.load_board_from_image(board_image)

    return {"fen": board.fen()}
