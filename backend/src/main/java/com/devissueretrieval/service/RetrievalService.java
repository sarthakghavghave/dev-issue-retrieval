package com.devissueretrieval.service;

import java.util.List;
import java.util.Arrays;
import com.devissueretrieval.dto.SearchRequest;
import com.devissueretrieval.dto.SearchResult;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.ResponseEntity;

@Service
public class RetrievalService {

    private final RestTemplate restTemplate = new RestTemplate();
    public List<SearchResult> search(String query) {

        SearchRequest request = new SearchRequest();
        request.setQuery(query);

        ResponseEntity<SearchResult[]> response =
                restTemplate.postForEntity(
                        "http://localhost:8000/search",
                        request,
                        SearchResult[].class
                );

        return Arrays.asList(response.getBody());
    }
}