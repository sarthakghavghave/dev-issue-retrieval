package com.devissueretrieval.service;

import java.util.List;
import java.util.Arrays;
import com.devissueretrieval.dto.SearchRequest;
import com.devissueretrieval.dto.SearchResult;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.beans.factory.annotation.Value;

@Service
public class RetrievalService {

    @Value("${retrieval.api.url}")
    private String retrievalApiUrl;

    private final RestTemplate restTemplate = new RestTemplate();

    public List<SearchResult> search(String query) {

        SearchRequest request = new SearchRequest();
        request.setQuery(query);

        ResponseEntity<SearchResult[]> response =
                restTemplate.postForEntity(retrievalApiUrl, request, SearchResult[].class);

        return Arrays.asList(response.getBody());
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