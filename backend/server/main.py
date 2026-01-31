from fastapi import FastAPI, File, UploadFile
from PIL import Image

from core.board.detector import BoardDetector

app = FastAPI()


@app.post("/fen")
def get_fen(board_file: UploadFile = File(...)):
    board_image = Image.open(board_file.file)
    board_detector = BoardDetector()
    board = board_detector.load_board_from_image(board_image)

    return {"fen": board.fen()}
