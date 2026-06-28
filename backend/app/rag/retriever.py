# backend/app/rag/retriever.py

import os
import pickle
import faiss
import numpy as np
import json

import openai
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def embed_text(text):
    response = openai.embeddings.create(
        model="text-embedding-3-large",
        input=text,
        encoding_format="float"
    )
    return response.data[0].embedding

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
CHUNKS_META_PATH = os.path.join(DATA_DIR, "semantic_chunks_meta.pkl")
CHUNKS_FAISS_PATH = os.path.join(DATA_DIR, "semantic_chunks_faiss_flatip.idx")
PAGES_META_PATH = os.path.join(DATA_DIR, "pages_meta.pkl")
PAGES_FAISS_PATH = os.path.join(DATA_DIR, "pages_faiss_flatip.idx")
CORRECTIONS_PATH = os.path.join(DATA_DIR, "corrections_log.json")

def load_meta(path):
    with open(path, "rb") as f:
        return pickle.load(f)

def load_faiss_index(path):
    return faiss.read_index(path)

def load_corrections(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

chunks_meta = load_meta(CHUNKS_META_PATH)
chunks_index = load_faiss_index(CHUNKS_FAISS_PATH)
pages_meta = load_meta(PAGES_META_PATH)
pages_index = load_faiss_index(PAGES_FAISS_PATH)
corrections_log = load_corrections(CORRECTIONS_PATH)

def apply_corrections(meta_obj, obj_id, corrections_log):
    for corr in corrections_log:
        if corr.get("obj_id") == obj_id and corr.get("status") == "active":
            meta_obj[corr["field"]] = corr["new_value"]
    return meta_obj

def retrieve_chunks(query_embedding, top_k=25):
    D, I = chunks_index.search(np.array([query_embedding], dtype=np.float32), top_k)
    results = []
    for idx, score in zip(I[0], D[0]):
        obj = dict(chunks_meta[idx])
        obj_id = obj.get("chunk_id", idx)
        obj = apply_corrections(obj, obj_id, corrections_log)
        results.append((obj, float(score)))
    return results

def retrieve_pages(query_embedding, top_k=6):
    D, I = pages_index.search(np.array([query_embedding], dtype=np.float32), top_k)
    results = []
    for idx, score in zip(I[0], D[0]):
        obj = dict(pages_meta[idx])
        obj_id = obj.get("page_id", idx)
        obj = apply_corrections(obj, obj_id, corrections_log)
        results.append((obj, float(score)))
    return results
