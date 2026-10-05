#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def load(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)

def dump(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")

if __name__ == "__main__":
    source, target = sys.argv[1:3]
    dump(load(source), target)
