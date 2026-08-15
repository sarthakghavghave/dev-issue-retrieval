package com.devissueretrieval.service;

import java.util.Arrays;
import java.util.List;

import com.devissueretrieval.dto.SearchConfigDto;
import com.devissueretrieval.dto.SearchRequest;
import com.devissueretrieval.dto.SearchResult;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

@Service
public class RetrievalService {

    @Value("${retrieval.api.url}")
    private String retrievalApiUrl;

    @Value("${retrieval.search.top-k:10}")
    private int defaultTopK;

    @Value("${retrieval.search.final-k:5}")
    private int defaultFinalK;

    @Value("${retrieval.search.rerank-k:5}")
    private int defaultRerankK;

    @Value("${retrieval.search.use-reranker:true}")
    private boolean defaultUseReranker;

    private final RestTemplate restTemplate = new RestTemplate();

    public List<SearchResult> search(
            String query,
            Integer topK,
            Integer finalK,
            Integer rerankK,
            Boolean useReranker) {

        SearchRequest request = new SearchRequest();
        request.setQuery(query);
        request.setTopK(topK);
        request.setFinalK(finalK);
        request.setRerankK(rerankK);
        request.setUseReranker(useReranker);

        ResponseEntity<SearchResult[]> response =
                restTemplate.postForEntity(retrievalApiUrl, request, SearchResult[].class);

        SearchResult[] body = response.getBody();
        if (body == null) {
            return List.of();
        }
        return Arrays.asList(body);
    }

    public SearchConfigDto getSearchConfig() {
        try {
            String configUrl = retrievalApiUrl.replace("/search", "/search/config");
            SearchConfigDto config = restTemplate.getForObject(configUrl, SearchConfigDto.class);
            if (config != null) {
                return config;
            }
        } catch (Exception ex) {
            // fall back to local defaults
        }

        SearchConfigDto fallback = new SearchConfigDto();
        fallback.setTopK(defaultTopK);
        fallback.setFinalK(defaultFinalK);
        fallback.setRerankK(defaultRerankK);
        fallback.setUseReranker(defaultUseReranker);
        return fallback;
    }

    public long getNlpIndexSize() {
        try {
            String statsUrl = retrievalApiUrl.replace("/search", "/stats");
            java.util.Map<?, ?> stats = restTemplate.getForObject(statsUrl, java.util.Map.class);
            if (stats != null && stats.containsKey("index_size")) {
                return ((Number) stats.get("index_size")).longValue();
            }
        } catch (Exception ex) {
            // fallback
        }
        return 0;
    }
}
