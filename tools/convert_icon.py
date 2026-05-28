from PIL import Image
import sys

def convert(src, dst):
    img = Image.open(src).convert("RGBA")
    # Save as multi-size ICO
    img.save(dst, format="ICO", sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: convert_icon.py <source.png> <out.ico>")
        raise SystemExit(2)
    convert(sys.argv[1], sys.argv[2])
