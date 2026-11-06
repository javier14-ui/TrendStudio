"""Credenciales mediante DPAPI de Windows, vinculadas al usuario del equipo."""
import ctypes
from ctypes import wintypes
from pathlib import Path

class Blob(ctypes.Structure):
    _fields_=[('size',wintypes.DWORD),('data',ctypes.POINTER(ctypes.c_ubyte))]

def transform(raw,protect):
    buf=ctypes.create_string_buffer(raw); src=Blob(len(raw),ctypes.cast(buf,ctypes.POINTER(ctypes.c_ubyte))); dst=Blob()
    dll=ctypes.WinDLL('crypt32',use_last_error=True)
    fn=dll.CryptProtectData if protect else dll.CryptUnprotectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(Blob)]
    fn.restype=wintypes.BOOL
    if not fn(ctypes.byref(src),None,None,None,None,1,ctypes.byref(dst)): raise OSError('Windows no pudo proteger o leer la clave.')
    try: return ctypes.string_at(dst.data,dst.size)
    finally:
        free=ctypes.WinDLL('kernel32').LocalFree; free.argtypes=[ctypes.c_void_p]; free.restype=ctypes.c_void_p; free(dst.data)

def save(path,key):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    if key: path.write_bytes(transform(key.encode(),True))
    else: path.unlink(missing_ok=True)
def load(path):
    path=Path(path)
    return transform(path.read_bytes(),False).decode() if path.exists() else ''
