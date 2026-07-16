package com.devissueretrieval.controller;

import com.devissueretrieval.service.IssueService;
import com.devissueretrieval.scheduler.IssueScheduler;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.HashMap;
import java.util.Map;

@RestController
@RequestMapping("/api/ingest")
@RequiredArgsConstructor
public class IssueController {

    private final IssueService issueService;
    private final IssueScheduler issueScheduler;

    @GetMapping("/incremental")
    public Map<String, Object> fetchIssues() {
        issueService.fetchIncrementalIssues();
        Map<String, Object> body = new HashMap<>();
        body.put("status", "ok");
        body.put("message", "Incremental ingestion completed");
        body.put("schedulerRunning", issueScheduler.isRunning());
        return body;
    }

    @GetMapping("/backfill")
    public Map<String, Object> backfillIssues() {
        issueService.fetchHistoricalIssues();
        Map<String, Object> body = new HashMap<>();
        body.put("status", "ok");
        body.put("message", "Historical backfill completed");
        return body;
    }
}