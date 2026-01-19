import os

def detect_category(filename):
    ext = os.path.splitext(filename)[1].lower()

    if ext in [".pdf", ".docx", ".txt", ".pptx", ".xlsx"]:
        return "document"
    elif ext in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
        return "image"
    elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
        return "video"
    else:
        return "other"


def file_size_in_mb(file):
    return round(file.size / (1024 * 1024), 2)
