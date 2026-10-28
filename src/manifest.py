"""Rewrite the versionName of an APK's binary AndroidManifest.xml.

Only the string itself changes: the string pool is rebuilt around it, every other chunk is
copied byte for byte. The APK must be re-signed afterwards, because the manifest changed.
"""

from __future__ import annotations

import struct
import zipfile
from pathlib import Path

RES_STRING_POOL = 0x0001
RES_XML_START_ELEMENT = 0x0102
UTF8_FLAG = 1 << 8


def _read_pool(data: bytes, off: int):
    _, hdr, size, count, styles, flags, strings_start, styles_start = struct.unpack_from("<HHIIIIII", data, off)
    offsets = list(struct.unpack_from(f"<{count}I", data, off + hdr))
    style_offsets_at = off + hdr + 4 * count
    style_offsets = list(struct.unpack_from(f"<{styles}I", data, style_offsets_at)) if styles else []
    return {
        "off": off, "hdr": hdr, "size": size, "count": count, "styles": styles, "flags": flags,
        "strings_start": strings_start, "styles_start": styles_start,
        "offsets": offsets, "style_offsets": style_offsets, "end": off + size,
    }


def _decode(data: bytes, pool: dict, index: int) -> str:
    pos = pool["off"] + pool["strings_start"] + pool["offsets"][index]
    if pool["flags"] & UTF8_FLAG:
        n = data[pos]; pos += 1
        if n & 0x80:
            pos += 1
        blen = data[pos]; pos += 1
        if blen & 0x80:
            blen = ((blen & 0x7F) << 8) | data[pos]; pos += 1
        return data[pos:pos + blen].decode("utf-8")
    n = struct.unpack_from("<H", data, pos)[0]; pos += 2
    if n & 0x8000:
        n = ((n & 0x7FFF) << 16) | struct.unpack_from("<H", data, pos)[0]; pos += 2
    return data[pos:pos + 2 * n].decode("utf-16-le")


def _encode(text: str, utf8: bool) -> bytes:
    if utf8:
        raw = text.encode("utf-8")
        chars = len(text.encode("utf-16-le")) // 2
        out = bytes([chars]) if chars < 0x80 else struct.pack(">H", 0x8000 | chars)
        out += bytes([len(raw)]) if len(raw) < 0x80 else struct.pack(">H", 0x8000 | len(raw))
        return out + raw + b"\x00"
    units = text.encode("utf-16-le")
    n = len(units) // 2
    head = struct.pack("<H", n) if n < 0x8000 else struct.pack("<HH", 0x8000 | (n >> 16), n & 0xFFFF)
    return head + units + b"\x00\x00"


def _find_attr_string_index(data: bytes, pool: dict, element: str, attr: str) -> int:
    """String-pool index of the value of attribute ``attr`` on the first element named ``element``."""
    names = {i: _decode(data, pool, i) for i in range(pool["count"])}
    name_ids = {v: k for k, v in names.items()}
    pos = pool["end"]
    while pos < len(data):
        ctype, hdr, size = struct.unpack_from("<HHI", data, pos)
        if ctype == RES_XML_START_ELEMENT:
            name_idx = struct.unpack_from("<I", data, pos + 16 + 4)[0]
            if names.get(name_idx) == element:
                attr_start, attr_size, attr_count = struct.unpack_from("<HHH", data, pos + 16 + 8)
                for i in range(attr_count):
                    a = pos + 16 + attr_start + i * attr_size
                    a_name, a_raw = struct.unpack_from("<II", data, a + 4)
                    if names.get(a_name) == attr:
                        return a_raw
                raise RuntimeError(f"attribute {attr} not found on {element}")
        pos += size
    raise RuntimeError(f"element {element} not found")


def read_version_name(manifest: bytes) -> str:
    pool = _read_pool(manifest, 8)
    return _decode(manifest, pool, _find_attr_string_index(manifest, pool, "manifest", "versionName"))


def set_version_name_bytes(manifest: bytes, new_name: str) -> bytes:
    pool = _read_pool(manifest, 8)
    idx = _find_attr_string_index(manifest, pool, "manifest", "versionName")
    utf8 = bool(pool["flags"] & UTF8_FLAG)

    strings = [_decode(manifest, pool, i) for i in range(pool["count"])]
    strings[idx] = new_name
    encoded = [_encode(s, utf8) for s in strings]
    blob = b"".join(encoded)
    blob += b"\x00" * (-len(blob) % 4)

    offsets, pos = [], 0
    for e in encoded:
        offsets.append(pos)
        pos += len(e)

    styles_data = manifest[pool["off"] + pool["styles_start"]:pool["end"]] if pool["styles"] else b""
    head_len = pool["hdr"] + 4 * pool["count"] + 4 * pool["styles"]
    style_offsets_bytes = manifest[pool["off"] + pool["hdr"] + 4 * pool["count"]:pool["off"] + pool["hdr"] + 4 * pool["count"] + 4 * pool["styles"]]
    strings_start = head_len
    styles_start = strings_start + len(blob) if pool["styles"] else 0
    new_size = head_len + len(blob) + len(styles_data)

    header = struct.pack("<HHIIIIII", RES_STRING_POOL, pool["hdr"], new_size,
                         pool["count"], pool["styles"], pool["flags"], strings_start, styles_start)
    new_pool = (header + struct.pack(f"<{pool['count']}I", *offsets) + style_offsets_bytes + blob + styles_data)

    before = manifest[:pool["off"]]
    after = manifest[pool["end"]:]
    out = before + new_pool + after
    # The whole-file size lives in the header at offset 4.
    return out[:4] + struct.pack("<I", len(out)) + out[8:]


def _aligned_info(item: zipfile.ZipInfo, pos: int) -> zipfile.ZipInfo:
    """Copy of ``item`` whose data starts on the boundary Android needs, like zipalign.

    Stored .so files must start on a 4096-byte boundary and resources.arsc on 4 bytes.
    The padding goes into a zero extra field (id 0xD935), which is what zipalign writes.
    """
    info = zipfile.ZipInfo(item.filename, date_time=item.date_time)
    info.external_attr = item.external_attr
    info.create_system = item.create_system
    if item.filename.endswith(".so"):
        align = 4096
    elif item.filename == "resources.arsc":
        align = 4
    else:
        align = 0
    extra = b""
    if align and item.compress_type == zipfile.ZIP_STORED:
        nl = len(item.filename.encode("utf-8"))
        need = (-(pos + 30 + nl)) % align
        if need and need < 4:
            need += align
        if need:
            extra = struct.pack("<HH", 0xD935, need - 4) + b"\x00" * (need - 4)
    info.extra = extra
    info.compress_type = item.compress_type
    return info


def set_version_name(apk_in: Path, apk_out: Path, new_name: str) -> None:
    """Copy an APK, changing only AndroidManifest.xml's versionName and keeping alignment."""
    with zipfile.ZipFile(apk_in) as src, zipfile.ZipFile(apk_out, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "AndroidManifest.xml":
                data = set_version_name_bytes(data, new_name)
            info = _aligned_info(item, dst.fp.tell())
            dst.writestr(info, data)
