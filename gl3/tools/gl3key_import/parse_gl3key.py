# -*- coding: utf-8 -*-
"""
parse_gl3key.py - precte Gl3Key.dat (binarni MFC CArchive dump z
CGl3Keywords::Serialize, viz Gl3_Keywords.cpp) a prevede na JSON.

Format (odvozeno primo z CGl3Keywords::Serialize, ne odhadem - overeno
na prvnich bajtech souboru):
  LONG  version        (4B, vzdy 1)
  DWORD count          (4B, pocet zaznamu)
  count x zaznam:
    string HtmlHelpFile   (DWORD delka BEZ null bytu, pak delka+1 bajtu vc. null terminatoru)
    LONG   ObjType        (4B, enum OBJ_TYPE - viz Gl3_Keywords.h)
    string Key            (stejne kodovani jako HtmlHelpFile)
    string Syntax
    string Comment
    string Menu

Vsechny integery little-endian (x86/MFC na Windows).
"""
import struct
import json

OBJ_TYPE_NAMES = [
    "Type_", "TypeI", "TypeD", "TypeA", "TypeC", "TypeE", "TypeF", "TypeG",
    "TypeH", "TypeL", "TypeM", "TypeP", "TypeQ", "TypeR", "TypeS", "TypeT",
    "TypeU", "TypeV",
]


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def u32(self):
        val = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return val

    def i32(self):
        val = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return val

    def cstr(self):
        length = self.u32()
        raw = self.data[self.pos:self.pos + length + 1]  # vc. null terminatoru
        self.pos += length + 1
        assert raw[-1] == 0, "ocekavan null terminator na konci retezce (pos=%d)" % self.pos
        text = raw[:-1].decode("cp1250")  # ceska Windows-1250 (stara MFC aplikace, CHAR ne WCHAR)
        return text

    def eof(self):
        return self.pos >= len(self.data)


def parse(path):
    with open(path, "rb") as f:
        data = f.read()
    r = Reader(data)
    version = r.i32()
    count = r.u32()
    records = []
    for i in range(count):
        html_help_file = r.cstr()
        obj_type_val = r.i32()
        key = r.cstr()
        syntax = r.cstr()
        comment = r.cstr()
        menu = r.cstr()
        obj_type_name = OBJ_TYPE_NAMES[obj_type_val] if 0 <= obj_type_val < len(OBJ_TYPE_NAMES) else "UNKNOWN(%d)" % obj_type_val
        records.append({
            "key": key,
            "obj_type": obj_type_name,
            "syntax": syntax,
            "comment": comment,
            "menu": menu,
            "html_help_file": html_help_file,
        })
    assert r.eof(), "po %d zaznamech zbyva jeste %d bajtu (format nesedi?)" % (count, len(data) - r.pos)
    return version, records


if __name__ == "__main__":
    import sys
    version, records = parse(sys.argv[1] if len(sys.argv) > 1 else "Gl3Key.dat")
    print("version:", version, "count:", len(records))
    for rec in records[:10]:
        print(rec)
