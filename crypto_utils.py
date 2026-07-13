import ctypes
from ctypes import wintypes
import base64

# Load private instances of DLLs to avoid affecting other packages (like yt-dlp)
crypt32 = ctypes.WinDLL("crypt32")
kernel32 = ctypes.WinDLL("kernel32")

# Define Windows API structures
class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char))
    ]

# Define local functions
LocalFree = kernel32.LocalFree
LocalFree.argtypes = [wintypes.HLOCAL]
LocalFree.restype = wintypes.HLOCAL

CryptProtectData = crypt32.CryptProtectData
CryptProtectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),
    wintypes.LPCWSTR,
    ctypes.POINTER(DATA_BLOB),
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(DATA_BLOB)
]
CryptProtectData.restype = wintypes.BOOL

CryptUnprotectData = crypt32.CryptUnprotectData
CryptUnprotectData.argtypes = [
    ctypes.POINTER(DATA_BLOB),
    ctypes.c_void_p,
    ctypes.POINTER(DATA_BLOB),
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(DATA_BLOB)
]
CryptUnprotectData.restype = wintypes.BOOL

def encrypt_bytes(data: bytes) -> bytes:
    in_blob = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_char)))
    out_blob = DATA_BLOB()
    
    res = CryptProtectData(ctypes.byref(in_blob), "yt_downloader_secret", None, None, None, 0, ctypes.byref(out_blob))
    if not res:
        raise Exception("CryptProtectData failed")
        
    try:
        encrypted_data = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return encrypted_data
    finally:
        LocalFree(out_blob.pbData)

def decrypt_bytes(data: bytes) -> bytes:
    in_blob = DATA_BLOB(len(data), ctypes.cast(ctypes.create_string_buffer(data), ctypes.POINTER(ctypes.c_char)))
    out_blob = DATA_BLOB()
    
    res = CryptUnprotectData(ctypes.byref(in_blob), None, None, None, None, 0, ctypes.byref(out_blob))
    if not res:
        raise Exception("CryptUnprotectData failed")
        
    try:
        decrypted_data = ctypes.string_at(out_blob.pbData, out_blob.cbData)
        return decrypted_data
    finally:
        LocalFree(out_blob.pbData)

def encrypt_credentials(username, password) -> str:
    combined = f"{username}\n{password}".encode('utf-8')
    encrypted = encrypt_bytes(combined)
    return base64.b64encode(encrypted).decode('utf-8')

def decrypt_credentials(encrypted_str: str):
    try:
        encrypted_bytes = base64.b64decode(encrypted_str.encode('utf-8'))
        decrypted_bytes = decrypt_bytes(encrypted_bytes)
        parts = decrypted_bytes.decode('utf-8').split('\n', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        return None
    except Exception as e:
        print(f"Decryption failed: {e}")
        return None
