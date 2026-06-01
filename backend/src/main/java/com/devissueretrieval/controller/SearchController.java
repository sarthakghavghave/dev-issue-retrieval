package com.devissueretrieval.controller;

import java.util.List;
import com.devissueretrieval.service.RetrievalService;
import com.devissueretrieval.dto.SearchResult;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

@RestController
@RequestMapping("/api/search")
public class SearchController {

    private final RetrievalService retrievalService;
    public SearchController(RetrievalService retrievalService) {
        this.retrievalService = retrievalService;
    }

    @GetMapping
    public List<SearchResult> search(@RequestParam String query) {
        return retrievalService.search(query);
    }
}