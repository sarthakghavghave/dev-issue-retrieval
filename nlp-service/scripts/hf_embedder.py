import os
import requests
import numpy as np

class HFEmbedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{model_name}"
        self.token = os.getenv("HF_TOKEN")
        if not self.token:
            print("WARNING: HF_TOKEN is not set. Inference API may rate limit or fail.")

    def encode(self, texts, batch_size=None, convert_to_numpy=True, show_progress_bar=False, normalize_embeddings=False):
        if isinstance(texts, str):
            texts = [texts]
            is_single = True
        else:
            is_single = False

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Default batch size if not provided
        if batch_size is None:
            batch_size = 32

        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            response = requests.post(
                self.api_url, 
                headers=headers, 
                json={"inputs": batch_texts, "options": {"wait_for_model": True}}
            )
            response.raise_for_status()
            
            embeddings = response.json()
            all_embeddings.extend(embeddings)

        all_embeddings = np.array(all_embeddings, dtype=np.float32)
        
        # Normalize embeddings if requested (useful for inner-product based FAISS indexing)
        if normalize_embeddings:
            norms = np.linalg.norm(all_embeddings, axis=1, keepdims=True)
            all_embeddings = all_embeddings / np.maximum(norms, 1e-12)

        return all_embeddings[0] if is_single else all_embeddings

class HFReranker:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.api_url = f"https://api-inference.huggingface.co/models/{model_name}"
        self.token = os.getenv("HF_TOKEN")

    def predict(self, pairs):
        if not pairs:
            return []
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        inputs = [{"text": q, "text_pair": d} for q, d in pairs]
        response = requests.post(
            self.api_url, 
            headers=headers, 
            json={"inputs": inputs, "options": {"wait_for_model": True}}
        )
        response.raise_for_status()
        
        data = response.json()
        scores = []
        for item in data:
            if isinstance(item, list):
                pos_score = next((l.get("score") for l in item if l.get("label") in ["LABEL_1", "1", "positive"]), item[0].get("score", 0.0))
                scores.append(pos_score)
            elif isinstance(item, dict):
                scores.append(item.get("score", 0.0))
            else:
                scores.append(0.0)
        return scores
