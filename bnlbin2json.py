#!/usr/bin/env python3
"""bnlbin2json.py
Convert .bnlbin (zlib-compressed JSON) files back to standard JSON.

Usage:
  python bnlbin2json.py -i <input.bnlbin> -o <output.json>
"""
import argparse
import json
import sys
import zlib

def from_bnlbin(filepath):
    with open(filepath, 'rb') as f:
        bdata = f.read()
    
    # Decompress zlib data
    dec = zlib.decompress(bdata)
    
    # Decode to string and parse JSON natively to ensure it's valid,
    # then return the structured object.
    text = dec.decode('utf-8')
    return json.loads(text)

def main(argv):
    p = argparse.ArgumentParser(description="Convert .bnlbin to .json")
    p.add_argument('-i', '--input', required=True, help='Input .bnlbin file')
    p.add_argument('-o', '--output', required=True, help='Output .json file')
    p.add_argument('--indent', type=int, default=2, help='Spaces for JSON indentation (default: 2)')
    
    args = p.parse_args(argv)
    
    try:
        obj = from_bnlbin(args.input)
    except Exception as e:
        print(f"Error reading or decompressing {args.input}: {e}")
        sys.exit(1)
        
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(obj, f, indent=args.indent, ensure_ascii=False)
        print(f"Successfully converted {args.input} to {args.output}")
    except Exception as e:
        print(f"Error writing to {args.output}: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main(sys.argv[1:])
