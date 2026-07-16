package com.devissueretrieval.scheduler;

import com.devissueretrieval.service.IssueService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.concurrent.atomic.AtomicBoolean;

@Component
@RequiredArgsConstructor
@Slf4j
public class IssueScheduler {

    private final IssueService issueService;

    private final AtomicBoolean running = new AtomicBoolean(false);
    
    private volatile LocalDateTime lastSuccessfulRun;
    
    @Value("${issue.ingestion.fixed-rate:21600000}")
    private long fixedRate;

    @Value("${issue.ingestion.initial-delay:60000}")
    private long initialDelay;

    @Scheduled(
            fixedRateString = "${issue.ingestion.fixed-rate:60000}",
            initialDelayString = "${issue.ingestion.initial-delay:60000}"
    )
    public void scheduleIssueIngestion() {
        if (!running.compareAndSet(false, true)) {
            log.warn("Previous ingestion run is still in progress; skipping this tick.");
            return;
        }
        try {
            log.info("Starting scheduled GitHub issue ingestion (fixedRate={} ms)...", fixedRate);
            issueService.fetchIncrementalIssues();
            lastSuccessfulRun = LocalDateTime.now(ZoneOffset.UTC);
            log.info("Issue ingestion completed.");
        } catch (Exception ex) {
            log.error("Scheduled ingestion failed", ex);
        } finally {
            running.set(false);
        }
    }

    public boolean isRunning() {
        return running.get();
    }

    public long getFixedRate() {
        return fixedRate;
    }
    
    public LocalDateTime getLastSuccessfulRun() {
        return lastSuccessfulRun;
    }
}