#!/usr/bin/env python3
"""json2bnlbin.py
Convert map JSON (or map folder with data.json + card.json) into .bnlbin (zlib-compressed JSON).

Usage:
  python json2bnlbin.py -i <input-file-or-dir> -o <output-file>

If input is a directory, script will look for 'data.json' and optional 'card.json' and assemble a container with keys:
  name, description, default_image, is_published, map (the data.json content)

If input is a file that contains top-level 'map', it will be used as-is and compressed.

Options:
  --level N   Compression level (0-9). Default: 9 (to match existing .bnlbin files)
  --verify    Decompress result and compare to original data for sanity check

"""
import argparse
import json
import os
import sys
import zlib


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def assemble_from_dir(d):
    data_path = os.path.join(d, 'data.json')
    card_path = os.path.join(d, 'card.json')
    if not os.path.isfile(data_path):
        raise FileNotFoundError(f"{data_path} not found in directory")
    data = load_json(data_path)
    container = {}
    if os.path.isfile(card_path):
        card = load_json(card_path)
        # card may have nested name/description
        name = None
        desc = None
        if isinstance(card.get('name'), dict):
            name = card['name'].get('text')
        elif isinstance(card.get('name'), str):
            name = card.get('name')
        if isinstance(card.get('description'), dict):
            desc = card['description'].get('text')
        elif isinstance(card.get('description'), str):
            desc = card.get('description')
        container['name'] = name or card.get('_id') or os.path.basename(d)
        container['description'] = desc or ''
        container['default_image'] = bool(card.get('image'))
        container['is_published'] = card.get('scope') == 'public'
    else:
        container['name'] = os.path.basename(d)
        container['description'] = ''
        container['default_image'] = False
        container['is_published'] = False
    container['map'] = data
    return container


def prepare_input(path):
    if os.path.isdir(path):
        return assemble_from_dir(path)
    if os.path.isfile(path):
        # First, try loading as plain JSON
        try:
            obj = load_json(path)
            if isinstance(obj, dict) and 'map' in obj:
                return obj
            # otherwise assume the file is the map content and wrap it:
            return {'name': os.path.splitext(os.path.basename(path))[0], 'description': '', 'default_image': False, 'is_published': False, 'map': obj}
        except Exception:
            # Not plain JSON — try JWT-like `header.payload.signature` mapdata files
            import base64
            import zlib
            s = open(path, 'rb').read().decode('utf-8')
            parts = s.split('.')
            if len(parts) >= 2:
                payload = parts[1]
                pad = '=' * ((4 - len(payload) % 4) % 4)
                try:
                    dec = base64.urlsafe_b64decode(payload + pad)
                    # payload might be raw JSON or compressed JSON (zlib)
                    try:
                        text = dec.decode('utf-8')
                    except Exception:
                        # try decompress
                        try:
                            text = zlib.decompress(dec).decode('utf-8')
                        except Exception as e:
                            raise ValueError('payload is not valid UTF-8 JSON or zlib-compressed JSON')
                    obj = json.loads(text)
                    if isinstance(obj, dict) and 'map' in obj:
                        return obj
                    return {'name': os.path.splitext(os.path.basename(path))[0], 'description': '', 'default_image': False, 'is_published': False, 'map': obj}
                except Exception as e:
                    raise ValueError(f'Failed to parse JWT-style payload from {path}: {e}')
    raise FileNotFoundError(path)


def to_bnlbin(obj, level=9):
    # Serialize compactly to match typical files
    raw = json.dumps(obj, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    return zlib.compress(raw, level=level)


def verify_bnlbin(bdata, expected_obj):
    dec = zlib.decompress(bdata)
    # decode and load JSON
    obj = json.loads(dec.decode('utf-8'))
    return obj == expected_obj


def main(argv):
    p = argparse.ArgumentParser()
    p.add_argument('-i', '--input', required=True, help='Input file or directory')
    p.add_argument('-o', '--output', required=True, help='Output .bnlbin file')
    p.add_argument('--level', type=int, default=9, help='zlib compression level 0-9 (default 9)')
    p.add_argument('--verify', action='store_true', help='Decompress and verify the output matches input')
    args = p.parse_args(argv)

    obj = prepare_input(args.input)
    b = to_bnlbin(obj, level=args.level)
    with open(args.output, 'wb') as f:
        f.write(b)
    print(f'Wrote {args.output} ({len(b)} bytes)')
    if args.verify:
        ok = verify_bnlbin(b, obj)
        print('Verify:', 'OK' if ok else 'FAILED')
        if not ok:
            # write decompressed for inspection
            with open(args.output + '.decompressed.json', 'wb') as f:
                f.write(zlib.decompress(b))
            print('Written decompressed JSON to', args.output + '.decompressed.json')


if __name__ == '__main__':
    main(sys.argv[1:])
