import tomllib

with open("pyproject.toml", "rb") as f:
    cfg = tomllib.load(f)

mongo_cfg = cfg["tool"]["mongo"]
chroma_cfg = cfg["tool"]["chroma"]

rag_cfg = cfg["tool"]["rag"]
