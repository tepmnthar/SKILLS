#!/usr/bin/env python3
"""Preprocess PO/POT files: clear non-Chinese msgstr and split into chunks."""

import argparse
import os
import re
import sys


def has_chinese(text):
    return bool(re.search(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', text))


def parse_entries(lines):
    """Split file lines into header block and individual msgid/msgstr entries."""
    entries = []
    current = []
    in_header = True

    for line in lines:
        stripped = line.rstrip('\n')
        if in_header:
            current.append(stripped)
            if stripped == '':
                in_header = False
                entries.append(current)
                current = []
            continue

        if stripped.startswith('msgid') and not stripped.startswith('msgid_plural'):
            if current:
                entries.append(current)
            current = [stripped]
        else:
            current.append(stripped)

    if current:
        entries.append(current)

    return entries


def clear_non_chinese_msgstr(entry_lines):
    """If msgstr has no Chinese characters, replace its value with empty string."""
    msgstr_idx = None
    for i, line in enumerate(entry_lines):
        if line.startswith('msgstr '):
            msgstr_idx = i
            break

    if msgstr_idx is None:
        return entry_lines

    msgstr_line = entry_lines[msgstr_idx]

    # Single-line msgstr like: msgstr "some text"
    m = re.match(r'^(msgstr )("(?:[^"\\]|\\.)*")(.*)$', msgstr_line)
    if m:
        value = m.group(2)
        suffix = m.group(3)
        if not has_chinese(value):
            return entry_lines[:msgstr_idx] + ['msgstr ""' + suffix] + entry_lines[msgstr_idx + 1:]
        return entry_lines

    # Multi-line msgstr: msgstr "" followed by continuation lines
    m2 = re.match(r'^(msgstr )("")(.*)$', msgstr_line)
    if m2:
        suffix = m2.group(3)
        cont_start = msgstr_idx + 1
        cont_lines = []
        for j in range(cont_start, len(entry_lines)):
            stripped = entry_lines[j].strip()
            if re.match(r'^"[^"]*"', stripped):
                cont_lines.append(entry_lines[j])
            else:
                break
        full_text = ''.join(cont_lines)
        if not has_chinese(full_text):
            return (entry_lines[:msgstr_idx]
                    + ['msgstr ""' + suffix]
                    + entry_lines[cont_start + len(cont_lines):])
        return entry_lines

    return entry_lines


def process_file(input_path, output_dir, max_entries=5000):
    basename = os.path.splitext(os.path.basename(input_path))[0]
    ext = os.path.splitext(input_path)[1]

    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    entries = parse_entries(lines)
    if not entries:
        print("No entries found in %s" % input_path)
        return

    # First entry is the header
    header = entries[0]
    data_entries = entries[1:]

    # Clear non-Chinese msgstr
    processed = [clear_non_chinese_msgstr(e) for e in data_entries]

    # Split into chunks
    total = len(processed)
    chunk_count = (total + max_entries - 1) // max_entries

    os.makedirs(output_dir, exist_ok=True)

    for i in range(chunk_count):
        start = i * max_entries
        end = min(start + max_entries, total)
        chunk = processed[start:end]

        part_num = str(i + 1).zfill(3)
        out_path = os.path.join(output_dir, "%s_part%s%s" % (basename, part_num, ext))

        with open(out_path, 'w', encoding='utf-8') as f:
            for line in header:
                f.write(line + '\n')
            for entry in chunk:
                for line in entry:
                    f.write(line + '\n')

        print("  %s: %d entries" % (out_path, len(chunk)))

    print("Total: %d entries -> %d file(s)" % (total, chunk_count))


def main():
    parser = argparse.ArgumentParser(
        description='Preprocess PO/POT files: clear non-Chinese msgstr and split into chunks.'
    )
    parser.add_argument('files', nargs='+', help='PO or POT file(s) to process')
    parser.add_argument('-o', '--output-dir', default='split',
                        help='Output directory (default: split/)')
    parser.add_argument('-n', '--max-entries', type=int, default=5000,
                        help='Max entries per split file (default: 5000)')
    args = parser.parse_args()

    for filepath in args.files:
        if not os.path.isfile(filepath):
            print("File not found: %s" % filepath, file=sys.stderr)
            sys.exit(1)
        print("\nProcessing: %s" % filepath)
        process_file(filepath, args.output_dir, args.max_entries)


if __name__ == '__main__':
    main()
