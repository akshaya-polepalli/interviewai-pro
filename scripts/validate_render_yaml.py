import json
import urllib.request
from pathlib import Path

import jsonschema
import yaml

sch = json.load(urllib.request.urlopen("https://render.com/schema/render.yaml.json"))
doc = yaml.safe_load(Path("render.yaml").read_text(encoding="utf-8"))
try:
    jsonschema.validate(doc, sch)
    print("VALID")
except jsonschema.ValidationError as e:
    print("INVALID")
    print("path:", list(e.absolute_path))
    print("message:", e.message)
