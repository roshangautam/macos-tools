"""Utility functions for formatting output."""

def format_size(size_bytes):
    """Format bytes into a human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def get_dir_size(path):
    """Calculate the total size of a directory."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for fname in filenames:
            file_path = os.path.join(dirpath, fname)
            try:
                total_size += os.path.getsize(file_path)
            except (OSError, FileNotFoundError):
                pass
    return total_size
