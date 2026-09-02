"""Compile ViaStitcher's gettext catalogs without external dependencies."""

from pathlib import Path
import ast
import struct


ROOT = Path(__file__).resolve().parent


def _unquote(value):
    return ast.literal_eval(value)


def read_po(path):
    messages = {}
    msgid = None
    msgstr = None
    active = None

    def store():
        if msgid is not None and msgstr is not None:
            messages[msgid] = msgstr

    for raw_line in path.read_text(encoding="utf-8-sig").splitlines() + [""]:
        line = raw_line.strip()
        if line.startswith("msgid "):
            store()
            msgid = _unquote(line[6:])
            msgstr = None
            active = "msgid"
        elif line.startswith("msgstr "):
            msgstr = _unquote(line[7:])
            active = "msgstr"
        elif line.startswith('"'):
            if active == "msgid":
                msgid += _unquote(line)
            elif active == "msgstr":
                msgstr += _unquote(line)
        elif not line:
            store()
            msgid = msgstr = active = None

    return messages


def write_mo(messages, path):
    keys = sorted(messages)
    ids = b""
    strings = b""
    id_offsets = []
    string_offsets = []

    for key in keys:
        encoded = key.encode("utf-8")
        id_offsets.append((len(encoded), len(ids)))
        ids += encoded + b"\0"

        encoded = messages[key].encode("utf-8")
        string_offsets.append((len(encoded), len(strings)))
        strings += encoded + b"\0"

    count = len(keys)
    key_table_offset = 7 * 4
    value_table_offset = key_table_offset + count * 8
    ids_offset = value_table_offset + count * 8
    strings_offset = ids_offset + len(ids)
    output = [struct.pack("<7I", 0x950412DE, 0, count, key_table_offset,
                          value_table_offset, 0, 0)]
    output.extend(struct.pack("<2I", length, ids_offset + offset)
                  for length, offset in id_offsets)
    output.extend(struct.pack("<2I", length, strings_offset + offset)
                  for length, offset in string_offsets)
    output.extend((ids, strings))
    path.write_bytes(b"".join(output))


def main():
    for po_path in sorted((ROOT / "locale").glob("*/LC_MESSAGES/viastitcher.po")):
        mo_path = po_path.with_suffix(".mo")
        write_mo(read_po(po_path), mo_path)
        print(f"Compiled {po_path.relative_to(ROOT)} -> {mo_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
