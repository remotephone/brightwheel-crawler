import os
import argparse
from datetime import datetime
import subprocess

def get_exif_date(image_path):
    try:
        exif_output = subprocess.check_output(['exiftool', '-Datecreate', image_path])
        exif_data = exif_output.decode().strip().split(': ')[-1]
        if exif_data:
            return datetime.strptime(exif_data, '%Y-%m-%dT%H:%M:%S+00:00')
    except Exception as e:
        print(f"Error reading EXIF data: {e}")
    return None

def rename_photo_with_date(image_path, live=False):
    date = get_exif_date(image_path)
    if date is None:
        print(f"No EXIF date found for {image_path}")
        return

    file_name = os.path.basename(image_path)
    new_file_name = f"{date.strftime('%Y_%m_%d')}_{file_name}"
    new_file_path = os.path.join(os.path.dirname(image_path), new_file_name)

    if live:
        try:
            os.rename(image_path, new_file_path)
            print(f"Renamed {image_path} to {new_file_path}")
        except Exception as e:
            print(f"Error renaming {image_path}: {e}")
    else:
        print(f"Dry run: Renaming {image_path} to {new_file_path}")

def rename_photos_recursive(path, live=False):
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                image_path = os.path.join(root, file)
                rename_photo_with_date(image_path, live)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Rename photos with EXIF date")
    parser.add_argument("--path", "-p", help="Path to the directory")
    parser.add_argument("--live", "-l", action="store_true", help="Perform live run (rename files)")
    args = parser.parse_args()

    rename_photos_recursive(args.path, args.live)