import chess
import cv2
import mlx.core as mx
import numpy as np
from chess_cv import load_bundled_model
from chess_cv.constants import get_model_config
from PIL import Image

pieces_model = load_bundled_model("pieces")
pieces_config = get_model_config("pieces")


class BoardDetector:
    MAX_DIMENSION = 1024  # Max width or height for processing

    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for chess board detection.

        Steps:
        1. Convert to grayscale (edges matter more than color)
        2. Resize if too large (performance optimization)
        3. Noise reduction (Gaussian blur)
        4. Contrast enhancement (histogram equalization)
        5. Edge sharpening

        Args:
            image: Input PIL Image

        Returns:
            Preprocessed PIL Image ready for board detection
        """
        image = np.array(image)
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        gaussian_blur = cv2.GaussianBlur(gray_image, (5, 5), 0)

        ret, otsu_binary = cv2.threshold(
            gaussian_blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

        canny = cv2.Canny(otsu_binary, 20, 255)

        kernel = np.ones((7, 7), np.uint8)

        img_dilation = cv2.dilate(canny, kernel, iterations=1)

        lines = cv2.HoughLinesP(
            img_dilation,
            1,
            np.pi / 180,
            threshold=200,
            minLineLength=100,
            maxLineGap=50,
        )

        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]

                # draws lines
                cv2.line(img_dilation, (x1, y1), (x2, y2), (255, 255, 255), 2)

        kernel = np.ones((3, 3), np.uint8)

        img_dilation_2 = cv2.dilate(img_dilation, kernel, iterations=1)

        board_contours, hierarchy = cv2.findContours(
            img_dilation_2, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )

        square_centers = list()

        # draw filtered rectangles to "canny" image for better visualization
        board_squared = canny.copy()

        for contour in board_contours:
            if 4000 < cv2.contourArea(contour) < 20000:
                # Approximate the contour to a simpler shape
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)

                # Ensure the approximated contour has 4 points (quadrilateral)
                if len(approx) == 4:
                    pts = [pt[0] for pt in approx]  # Extract coordinates

                    # Define the points explicitly
                    pt1 = tuple(pts[0])
                    pt2 = tuple(pts[1])
                    pt4 = tuple(pts[2])
                    pt3 = tuple(pts[3])

                    x, y, w, h = cv2.boundingRect(contour)
                    center_x = (x + (x + w)) / 2
                    center_y = (y + (y + h)) / 2

                    square_centers.append([center_x, center_y, pt2, pt1, pt3, pt4])

                    # Draw the lines between the points
                    cv2.line(board_squared, pt1, pt2, (255, 255, 0), 7)
                    cv2.line(board_squared, pt1, pt3, (255, 255, 0), 7)
                    cv2.line(board_squared, pt2, pt4, (255, 255, 0), 7)
                    cv2.line(board_squared, pt3, pt4, (255, 255, 0), 7)

        sorted_coordinates = sorted(square_centers, key=lambda x: x[1], reverse=True)

        if not sorted_coordinates:
            return board_squared

        groups = []
        current_group = [sorted_coordinates[0]]

        for coord in sorted_coordinates[1:]:
            if abs(coord[1] - current_group[-1][1]) < 50:
                current_group.append(coord)
            else:
                groups.append(current_group)
                current_group = [coord]

        # Append the last group
        groups.append(current_group)

        # Step 2: Sort each group by the second index (column values)
        for group in groups:
            group.sort(key=lambda x: x[0])

        # Step 3: Combine the groups back together
        sorted_coordinates = [coord for group in groups for coord in group]

        sorted_coordinates[:10]
        for num in range(len(sorted_coordinates) - 1):
            if abs(sorted_coordinates[num][1] - sorted_coordinates[num + 1][1]) < 50:
                if sorted_coordinates[num + 1][0] - sorted_coordinates[num][0] > 150:
                    x = (
                        sorted_coordinates[num + 1][0] + sorted_coordinates[num][0]
                    ) / 2
                    y = (
                        sorted_coordinates[num + 1][1] + sorted_coordinates[num][1]
                    ) / 2
                    p1 = sorted_coordinates[num + 1][5]
                    p2 = sorted_coordinates[num + 1][4]
                    p3 = sorted_coordinates[num][3]
                    p4 = sorted_coordinates[num][2]
                    sorted_coordinates.insert(num + 1, [x, y, p1, p2, p3, p4])

        square_num = 1
        for cor in sorted_coordinates:
            cv2.putText(
                img=board_squared,
                text=str(square_num),
                org=(int(cor[0]) - 30, int(cor[1])),
                fontFace=cv2.FONT_HERSHEY_DUPLEX,
                fontScale=1,
                color=(125, 246, 55),
                thickness=3,
            )
        square_num += 1

        return board_squared

    def find_corners(self, image: Image.Image) -> tuple[np.ndarray | None, np.ndarray]:
        """
        Find the four corners of a chess board in an image.

        Args:
            image: Input PIL Image

        Returns:
            Tuple of (corners, debug_image) where:
            - corners: 4x2 numpy array of corner points ordered as
                       [top-left, top-right, bottom-right, bottom-left],
                       or None if no board found
            - debug_image: Image with detected corners drawn for visualization
        """
        img = np.array(image)
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        debug_img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        edges = cv2.Canny(binary, 50, 150)

        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=2)

        contours, _ = cv2.findContours(
            dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        if not contours:
            return None, debug_img

        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        corners = None
        for contour in contours[:10]:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)

            if len(approx) == 4 and cv2.contourArea(contour) > 10000:
                corners = approx.reshape(4, 2)
                break

        if corners is None:
            return None, debug_img

        corners = self._order_corners(corners)

        colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0)]
        labels = ["TL", "TR", "BR", "BL"]

        for corner, color, label in zip(corners, colors, labels, strict=False):
            x, y = int(corner[0]), int(corner[1])
            cv2.circle(debug_img, (x, y), 10, color, -1)
            cv2.putText(
                debug_img,
                label,
                (x + 15, y + 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2,
            )

        cv2.polylines(debug_img, [corners.astype(np.int32)], True, (0, 255, 0), 2)

        return corners, debug_img

    def _order_corners(self, corners: np.ndarray) -> np.ndarray:
        """Order corners as: top-left, top-right, bottom-right, bottom-left."""
        sorted_by_y = corners[np.argsort(corners[:, 1])]
        top_points = sorted_by_y[:2]
        bottom_points = sorted_by_y[2:]

        top_left, top_right = top_points[np.argsort(top_points[:, 0])]
        bottom_left, bottom_right = bottom_points[np.argsort(bottom_points[:, 0])]

        return np.array(
            [top_left, top_right, bottom_right, bottom_left], dtype=np.float32
        )

    def warp_board(
        self, image: Image.Image, corners: np.ndarray, output_size: int = 800
    ) -> np.ndarray:
        """Apply perspective transform to extract a top-down square view of the board."""
        img = np.array(image)

        src_points = corners.astype(np.float32)
        dst_points = np.array(
            [
                [0, 0],
                [output_size - 1, 0],
                [output_size - 1, output_size - 1],
                [0, output_size - 1],
            ],
            dtype=np.float32,
        )

        matrix = cv2.getPerspectiveTransform(src_points, dst_points)
        return cv2.warpPerspective(img, matrix, (output_size, output_size))

    def extract_squares(self, warped_board: np.ndarray) -> dict[str, np.ndarray]:
        """Divide the warped board into 64 square images. Assumes white at bottom."""
        height, width = warped_board.shape[:2]
        square_h, square_w = height // 8, width // 8

        squares = {}
        for row, rank in enumerate("87654321"):
            for col, file in enumerate("abcdefgh"):
                y0, y1 = row * square_h, (row + 1) * square_h
                x0, x1 = col * square_w, (col + 1) * square_w
                squares[f"{file}{rank}"] = warped_board[y0:y1, x0:x1]

        return squares

    def detect_piece(self, piece_image: np.ndarray, pieces_model) -> str:
        """Detect the chess piece in a given square image using the provided model."""
        piece_image = piece_image.astype(np.float32) / 255.0
        piece_image = cv2.resize(piece_image, (32, 32))
        img_tensor = mx.array(piece_image[None, ...])
        logits = pieces_model(img_tensor)
        probabilities = mx.softmax(logits, axis=-1)
        predicted_class = mx.argmax(probabilities, axis=-1).item()
        return pieces_config["class_names"][predicted_class]

    def load_board_from_image(self, image: Image.Image) -> chess.Board | None:
        """Detect chess position from an image and return a chess.Board."""
        corners, _ = self.find_corners(image)
        if corners is None:
            return None

        warped = self.warp_board(image, corners)
        squares = self.extract_squares(warped)

        piece_map = {
            "wP": chess.Piece(chess.PAWN, chess.WHITE),
            "wN": chess.Piece(chess.KNIGHT, chess.WHITE),
            "wB": chess.Piece(chess.BISHOP, chess.WHITE),
            "wR": chess.Piece(chess.ROOK, chess.WHITE),
            "wQ": chess.Piece(chess.QUEEN, chess.WHITE),
            "wK": chess.Piece(chess.KING, chess.WHITE),
            "bP": chess.Piece(chess.PAWN, chess.BLACK),
            "bN": chess.Piece(chess.KNIGHT, chess.BLACK),
            "bB": chess.Piece(chess.BISHOP, chess.BLACK),
            "bR": chess.Piece(chess.ROOK, chess.BLACK),
            "bQ": chess.Piece(chess.QUEEN, chess.BLACK),
            "bK": chess.Piece(chess.KING, chess.BLACK),
        }

        board = chess.Board.empty()
        for square_name, square_img in squares.items():
            piece_class = self.detect_piece(square_img, pieces_model)
            if piece_class != "xx":
                square = chess.parse_square(square_name)
                board.set_piece_at(square, piece_map[piece_class])

        return board
