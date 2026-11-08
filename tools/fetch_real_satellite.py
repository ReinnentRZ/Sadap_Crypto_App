"""
Utility script to fetch real high-resolution satellite imagery from Earth observation servers.
"""
import urllib.request
from pathlib import Path

LOCATIONS = {
    "sat_nusantara.png": "bbox=116.65,-1.05,116.95,-0.85",
    "sat_krakatau.png": "bbox=105.35,-6.18,105.55,-6.02",
    "sat_tokyo.png": "bbox=139.65,35.55,139.9,35.75",
    "sat_fuji.png": "bbox=138.65,35.3,138.85,35.45"
}

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "sample_images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def fetch_all():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for filename, bbox in LOCATIONS.items():
        out_file = OUTPUT_DIR / filename
        if out_file.exists() and out_file.stat().st_size > 10000:
            print(f"Skipping {filename}, already exists ({out_file.stat().st_size} bytes).")
            continue

        url = f"https://services.arcgisonline.com/arcgis/rest/services/World_Imagery/MapServer/export?{bbox}&bboxSR=4326&imageSR=4326&size=640,480&f=image"
        print(f"Fetching {filename} from satellite server...")
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                data = response.read()
                out_file.write_bytes(data)
                print(f"Saved {filename} ({len(data)} bytes).")
        except Exception as e:
            print(f"Failed to fetch {filename}: {e}")


if __name__ == "__main__":
    fetch_all()
