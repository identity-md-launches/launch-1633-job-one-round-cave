#!/usr/bin/env python3
"""Composite the in-memory generated pigment insert onto Pepe 24's exact wall."""

import base64
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
WALL = ROOT / 'artifacts' / 'line-2' / 'wall-v5.png'
EXPECTED_SOURCE_SHA256 = 'cd80330d897598928f981281cb2443a05994963ce62cb908108b037b7b917e5c'
PLACE_X, PLACE_Y, PLACE_W, PLACE_H = 872, 570, 220, 136
OPACITY = 0.96


def decode_png(blob):
    if blob[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('input is not PNG')
    pos, header, compressed = 8, None, bytearray()
    while pos < len(blob):
        length = int.from_bytes(blob[pos:pos + 4], 'big')
        kind = blob[pos + 4:pos + 8]
        payload = blob[pos + 8:pos + 8 + length]
        crc = int.from_bytes(blob[pos + 8 + length:pos + 12 + length], 'big')
        if zlib.crc32(kind + payload) != crc:
            raise ValueError('PNG chunk CRC mismatch')
        if kind == b'IHDR':
            header = struct.unpack('>IIBBBBB', payload)
        elif kind == b'IDAT':
            compressed.extend(payload)
        elif kind == b'IEND':
            break
        pos += length + 12
    if header is None:
        raise ValueError('PNG has no IHDR')
    width, height, depth, color, comp, filt, interlace = header
    if depth != 8 or color not in (2, 6) or comp != 0 or filt != 0 or interlace != 0:
        raise ValueError('expected non-interlaced 8-bit RGB or RGBA PNG')
    channels = 3 if color == 2 else 4
    stride = width * channels
    raw = zlib.decompress(compressed)
    if len(raw) != (stride + 1) * height:
        raise ValueError('PNG scanline length mismatch')
    previous, rows = bytearray(stride), []
    for y in range(height):
        offset = y * (stride + 1)
        mode = raw[offset]
        row = bytearray(raw[offset + 1:offset + 1 + stride])
        if mode not in range(5):
            raise ValueError('unsupported PNG filter')
        for x in range(stride):
            a = row[x - channels] if x >= channels else 0
            b = previous[x]
            c = previous[x - channels] if x >= channels else 0
            if mode == 1:
                predictor = a
            elif mode == 2:
                predictor = b
            elif mode == 3:
                predictor = (a + b) // 2
            elif mode == 4:
                p = a + b - c
                distances = (abs(p - a), abs(p - b), abs(p - c))
                predictor = (a, b, c)[distances.index(min(distances))]
            else:
                predictor = 0
            row[x] = (row[x] + predictor) & 255
        rows.append(bytes(row))
        previous = row
    return width, height, channels, rows


def encode_rgb_png(width, height, rows):
    raw = b''.join(b'\0' + row for row in rows)

    def chunk(kind, payload):
        return (struct.pack('>I', len(payload)) + kind + payload
                + struct.pack('>I', zlib.crc32(kind + payload)))

    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw, 9))
            + chunk(b'IEND', b''))


def composite(base_rows, motif):
    width, height, channels, rows = motif
    if channels != 4:
        raise ValueError('the pigment insert must have an alpha channel')
    bounds = [width, height, 0, 0]
    for y, row in enumerate(rows):
        for x in range(width):
            if row[x * 4 + 3] > 16:
                bounds[0] = min(bounds[0], x)
                bounds[1] = min(bounds[1], y)
                bounds[2] = max(bounds[2], x + 1)
                bounds[3] = max(bounds[3], y + 1)
    x0, y0, x1, y1 = bounds
    if x1 <= x0 or y1 <= y0:
        raise ValueError('pigment insert has no visible pixels')
    if PLACE_X + PLACE_W > len(base_rows[0]) // 3 or PLACE_Y + PLACE_H > len(base_rows):
        raise ValueError('placement rectangle lies outside the inherited wall')

    result = [bytearray(row) for row in base_rows]
    crop_w, crop_h = x1 - x0, y1 - y0
    for dy in range(PLACE_H):
        sy0 = y0 + dy * crop_h / PLACE_H
        sy1 = y0 + (dy + 1) * crop_h / PLACE_H
        for dx in range(PLACE_W):
            sx0 = x0 + dx * crop_w / PLACE_W
            sx1 = x0 + (dx + 1) * crop_w / PLACE_W
            alpha_total, color_total = 0.0, [0.0, 0.0, 0.0]
            for sy in range(math.floor(sy0), math.ceil(sy1)):
                wy = max(0.0, min(sy1, sy + 1) - max(sy0, sy))
                if not wy:
                    continue
                source_row = rows[sy]
                for sx in range(math.floor(sx0), math.ceil(sx1)):
                    wx = max(0.0, min(sx1, sx + 1) - max(sx0, sx))
                    weight = wx * wy
                    source = sx * 4
                    alpha = source_row[source + 3] / 255.0
                    amount = weight * alpha
                    alpha_total += amount
                    for channel in range(3):
                        color_total[channel] += source_row[source + channel] * amount
            if alpha_total == 0:
                continue
            source_color = [value / alpha_total for value in color_total]
            average_alpha = alpha_total / ((sx1 - sx0) * (sy1 - sy0))
            opacity = min(1.0, average_alpha ** 0.72) * OPACITY
            px, py = PLACE_X + dx, PLACE_Y + dy
            target = result[py]
            offset = px * 3
            for channel in range(3):
                target[offset + channel] = round(
                    target[offset + channel] * (1.0 - opacity)
                    + source_color[channel] * opacity)
    return [bytes(row) for row in result], bounds


def main():
    if len(sys.argv) != 2 or not sys.argv[1].isdecimal():
        raise SystemExit('usage: finish_wall_25.py BASE64_CHARACTER_COUNT < pigment-insert-base64')
    char_count = int(sys.argv[1])
    encoded = sys.stdin.buffer.read(char_count)
    if len(encoded) != char_count:
        raise ValueError('truncated base64 input')
    insert = base64.b64decode(encoded, validate=True)
    original = WALL.read_bytes()
    source_hash = hashlib.sha256(original).hexdigest()
    if source_hash != EXPECTED_SOURCE_SHA256:
        raise ValueError('wall is not the untouched, verified Pepe 24 source; refusing to composite twice')
    width, height, channels, base = decode_png(original)
    if channels != 3 or width != height:
        raise ValueError('expected the inherited square RGB cave wall')
    motif = decode_png(insert)
    final_rows, bounds = composite(base, motif)
    for y, (before, after) in enumerate(zip(base, final_rows)):
        if y < PLACE_Y or y >= PLACE_Y + PLACE_H:
            if before != after:
                raise ValueError('composite changed a row outside its placement rectangle')
            continue
        split_left, split_right = PLACE_X * 3, (PLACE_X + PLACE_W) * 3
        if before[:split_left] != after[:split_left] or before[split_right:] != after[split_right:]:
            raise ValueError('composite changed pixels outside its placement rectangle')
    output = encode_rgb_png(width, height, final_rows)
    WALL.write_bytes(output)
    print(json.dumps({
        'wall': str(WALL.relative_to(ROOT)),
        'dimensions': [width, height],
        'source_sha256': source_hash,
        'motif_source_dimensions': [motif[0], motif[1]],
        'motif_alpha_bounds': bounds,
        'placement_rectangle': [PLACE_X, PLACE_Y, PLACE_W, PLACE_H],
        'outside_placement_unchanged': True,
        'output_sha256': hashlib.sha256(output).hexdigest(),
        'output_bytes': len(output),
    }))


if __name__ == '__main__':
    main()
