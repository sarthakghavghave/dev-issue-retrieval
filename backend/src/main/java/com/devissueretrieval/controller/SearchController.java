package com.devissueretrieval.controller;

import java.util.List;
import java.util.Map;
import java.util.HashMap;
import com.devissueretrieval.service.RetrievalService;
import com.devissueretrieval.repository.IssueRepository;
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
    public List<SearchResult> search(@RequestParam String query) {
        return retrievalService.search(query);
    }

    @GetMapping("/stats")
    public Map<String, Object> getStats() {
        Map<String, Object> stats = new HashMap<>();
        stats.put("totalIssues", issueRepository.count());
        stats.put("totalRepositories", issueRepository.countDistinctRepositoryNames());
        return stats;
    }
}