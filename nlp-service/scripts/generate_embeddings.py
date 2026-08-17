import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import faiss
import numpy as np
import pandas as pd

from scripts.config import CSV_PATH, INDEX_PATH, METADATA_PATH, MODEL_NAME, EMBEDDINGS_PATH
from scripts.hf_embedder import HFEmbedder

df = pd.read_csv(CSV_PATH)
df = df.dropna(subset=["retrieval_text"])
texts = df["retrieval_text"].tolist()

print(f"\nTotal documents: {len(texts)}")

model = HFEmbedder(MODEL_NAME)
embeddings = model.encode(
    texts,
    batch_size=32,
    show_progress_bar=False,
    convert_to_numpy=True,
    normalize_embeddings=True
)

np.save(EMBEDDINGS_PATH, embeddings)

dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(embeddings)

faiss.write_index(index, str(INDEX_PATH))
df.to_parquet(METADATA_PATH, index=False)

print("\nEmbedding generation completed.")
print("\nEmbedding shape:", embeddings.shape)
