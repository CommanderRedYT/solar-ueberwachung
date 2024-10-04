# grab a image from camera streamer every 5 seconds, embed the image with a timestamp and save it to a local directory
# to grab a image, we use the following url: http://raspi-01:8080/snapshot
from io import BytesIO

import requests
import time
import datetime
import os

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw


def format_byte_size(bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes < 1024:
            return f"{bytes:.2f} {unit}"
        bytes /= 1024
    return f"{bytes:.2f} PB"


# url to grab the image
CAMERA_HOSTNAME = "raspi-01"
CAMERA_PORT = 8080
CAMERA_BASE_URL = f"http://{CAMERA_HOSTNAME}:{CAMERA_PORT}"
CAMERA_SNAPSHOT_URL = f"{CAMERA_BASE_URL}/snapshot"
CAMERA_STATUS_URL = f"{CAMERA_BASE_URL}/status"

# opendtu
OPENDTU_HOSTNAME = "192.168.0.128"
OPENDTU_PORT = 80
OPENDTU_STATUS_URL = f"http://{OPENDTU_HOSTNAME}:{OPENDTU_PORT}/api/livedata/status"

# local directory to save the image
SAVE_DIR = "images"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S %Z"
TIME_ZONE = "Europe/Vienna"
TIMEOUT = 2

# create the directory if it does not exist
if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)


def get_opendtu_data():
    response = requests.get(OPENDTU_STATUS_URL)

    return response.json()


def format_opendtu_value(field) -> str:
    if not field:
        return "N/A"

    value = field.get("v", 0)
    unit = field.get("u", "")
    decimals = field.get("d", 0)

    return f"{value:.{decimals}f} {unit}"


def get_camera_status():
    response = requests.get(CAMERA_STATUS_URL)
    return response.json()


def get_image():
    response = requests.get(CAMERA_SNAPSHOT_URL)

    now = datetime.datetime.now()

    return Image.open(BytesIO(response.content)), now


def embed_text(image, now):
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(30)

    timestamp = now.astimezone().strftime(TIME_FORMAT)

    opendtu_data = get_opendtu_data()

    power = opendtu_data.get("total", {}).get("Power", {})
    power_string = f"Power: {format_opendtu_value(power)}"

    yield_day = opendtu_data.get("total", {}).get("YieldDay", {})
    yield_day_string = f"Yield Today: {format_opendtu_value(yield_day)}"

    draw.text((10, 10), timestamp, font=font, fill="white", stroke_width=4, stroke_fill="black")

    draw.text((10, 40), power_string, font=font, fill="white", stroke_width=4, stroke_fill="black")

    draw.text((10, 70), yield_day_string, font=font, fill="white", stroke_width=4, stroke_fill="black")

    return image


def save_image(image, now):
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    filename = f"{SAVE_DIR}/image_{timestamp}.jpg"
    image.save(filename)
    print(f"Image saved to {filename}")


def estimate_size_per_hour():
    image, _ = get_image()

    image.save("test.jpg")
    size = os.path.getsize("test.jpg")
    os.remove("test.jpg")

    return size * 3600 / TIMEOUT


def estimate_frames_per_hour():
    return 3600 / TIMEOUT


def main():
    status = get_camera_status()
    outputs = status.get("outputs", {})

    if not outputs.get("snapshot", False):
        raise RuntimeError("Snapshot output is not enabled")

    snapshot = outputs["snapshot"]

    height = snapshot.get("height", 0)
    width = snapshot.get("width", 0)

    if height == 0 or width == 0:
        raise RuntimeError("Invalid snapshot resolution")

    print(f"Snapshot resolution: {width}x{height}")

    size_per_hour = estimate_size_per_hour()
    frames_per_hour = estimate_frames_per_hour()

    print(f"Estimated size per hour: {format_byte_size(size_per_hour)} ({frames_per_hour} frames)")

    while True:
        image, now = get_image()
        image = embed_text(image, now)
        save_image(image, now)
        time.sleep(TIMEOUT)


if __name__ == "__main__":
    main()
