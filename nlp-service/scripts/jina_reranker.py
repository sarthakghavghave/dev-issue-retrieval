import os
import requests

class JinaReranker:
    def __init__(self):
        self.api_url = "https://api.jina.ai/v1/rerank"
        self.token = os.getenv("JINA_API_KEY")

    def predict(self, pairs):
        if not pairs:
            return []

        if not self.token:
            raise ValueError("JINA_API_KEY is not configured")

        query = pairs[0][0]
        documents = [pair[1] for pair in pairs]

        response = requests.post(
            self.api_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            },
            json={
                "model": "jina-reranker-v2-base-multilingual",
                "query": query,
                "documents": documents,
                "top_n": len(documents),
                "return_documents": False
            },
            timeout=120
        )

        response.raise_for_status()

        data = response.json()["results"]

        scores = [0.0] * len(documents)

        for item in data:
            scores[item["index"]] = item["relevance_score"]

        return scores