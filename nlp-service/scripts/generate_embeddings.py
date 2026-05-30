import numpy as np
import pandas as pd
import faiss

from sentence_transformers import SentenceTransformer
from pathlib import Path
from tqdm import tqdm

MODEL_NAME = "BAAI/bge-small-en-v1.5"

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "data/processed/cleaned_issues.csv"
EMBEDDINGS_PATH = BASE_DIR / "data/embeddings/issue_embeddings.npy"
INDEX_PATH = BASE_DIR / "data/embeddings/faiss_index.index"
METADATA_PATH = BASE_DIR / "data/embeddings/metadata.parquet"

df = pd.read_csv(CSV_PATH)
df = df.dropna(subset=["retrieval_text"])
texts = df["retrieval_text"].tolist()

print(f"\nTotal documents: {len(texts)}")

model = SentenceTransformer(MODEL_NAME)
embeddings = model.encode(
    texts,
    batch_size=32,
    show_progress_bar=True,
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
