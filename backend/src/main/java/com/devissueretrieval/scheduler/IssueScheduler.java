package com.devissueretrieval.scheduler;

import com.devissueretrieval.service.IssueService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

@Component
@RequiredArgsConstructor
@Slf4j
public class IssueScheduler {

    private final IssueService issueService;

//    @Scheduled(fixedRate = 60000) // 1 min. 6 hr = 21600000 ms
    public void scheduleIssueIngestion() {
        log.info("Starting scheduled GitHub issue ingestion...");
        issueService.fetchIncrementalIssues();
        log.info("Issue ingestion completed.");
    }
}