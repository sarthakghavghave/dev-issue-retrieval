package com.devissueretrieval.controller;

import com.devissueretrieval.service.IssueService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
public class IssueController {

    private final IssueService issueService;

    @GetMapping("/fetch")
    public String fetchIssues() {
        issueService.fetchIncrementalIssues();
        return "Issues fetched successfully";
    }

    // Temporary endpoint for historical backfill
    @GetMapping("/backfill")
    public String backfillIssues() {
        issueService.fetchHistoricalIssues();
        return "Historical backfill completed";
    }
}