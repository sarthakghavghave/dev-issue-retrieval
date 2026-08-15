package com.devissueretrieval.controller;

import java.util.List;
import java.util.Map;
import java.util.HashMap;
import com.devissueretrieval.model.IndexStatus;
import com.devissueretrieval.service.RetrievalService;
import com.devissueretrieval.repository.IssueRepository;
import com.devissueretrieval.dto.SearchConfigDto;
import com.devissueretrieval.dto.SearchResult;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;

@RestController
@RequestMapping("/api/search")
public class SearchController {

    private final RetrievalService retrievalService;
    private final IssueRepository issueRepository;

    public SearchController(RetrievalService retrievalService, IssueRepository issueRepository) {
        this.retrievalService = retrievalService;
        this.issueRepository = issueRepository;
    }

    @GetMapping
    public List<SearchResult> search(
            @RequestParam String query,
            @RequestParam(required = false) Integer topK,
            @RequestParam(required = false) Integer finalK,
            @RequestParam(required = false) Integer rerankK,
            @RequestParam(required = false) Boolean useReranker) {
        return retrievalService.search(query, topK, finalK, rerankK, useReranker);
    }

    @GetMapping("/config")
    public SearchConfigDto getSearchConfig() {
        return retrievalService.getSearchConfig();
    }

    @GetMapping("/stats")
    public Map<String, Object> getStats() {
        Map<String, Object> stats = new HashMap<>();
        long indexedCount = issueRepository.countByIndexStatus(IndexStatus.INDEXED);
        stats.put("totalIssues", indexedCount > 0 ? indexedCount : issueRepository.count());
        stats.put("totalRepositories", issueRepository.countDistinctRepositoryNames());
        return stats;
    }
}