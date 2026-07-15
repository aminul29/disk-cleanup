from __future__ import annotations

import base64
import ctypes
from ctypes import wintypes


CRYPTPROTECT_UI_FORBIDDEN = 0x1
SECRET_PREFIX = "dpapi:"


class DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_byte)),
    ]


def protect_secret(value: str) -> str:
    if not value:
        return ""
    plaintext = value.encode("utf-8")
    input_buffer = ctypes.create_string_buffer(plaintext)
    input_blob = DataBlob(
        len(plaintext),
        ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_byte)),
    )
    output_blob = DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        "DiskWise AI local secret",
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()
    try:
        encrypted = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return SECRET_PREFIX + base64.b64encode(encrypted).decode("ascii")
    finally:
        kernel32.LocalFree(output_blob.pbData)


def unprotect_secret(value: str) -> str:
    if not value:
        return ""
    if not value.startswith(SECRET_PREFIX):
        raise ValueError("Secret is not protected with Windows DPAPI")
    encrypted = base64.b64decode(value[len(SECRET_PREFIX) :], validate=True)
    input_buffer = ctypes.create_string_buffer(encrypted)
    input_blob = DataBlob(
        len(encrypted),
        ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_byte)),
    )
    output_blob = DataBlob()
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    if not crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    ):
        raise ctypes.WinError()
    try:
        plaintext = ctypes.string_at(output_blob.pbData, output_blob.cbData)
        return plaintext.decode("utf-8")
    finally:
        kernel32.LocalFree(output_blob.pbData)
