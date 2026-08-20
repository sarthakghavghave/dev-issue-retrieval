package com.devissueretrieval.controller;

import com.devissueretrieval.dto.IndexStatsDto;
import com.devissueretrieval.scheduler.IssueScheduler;
import com.devissueretrieval.service.StatsService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.format.DateTimeFormatter;

@RestController
@RequestMapping("/api/stats")
@RequiredArgsConstructor
public class StatsController {

    private final StatsService statsService;
    private final IssueScheduler issueScheduler;

    @GetMapping
    public IndexStatsDto getStats() {
        String lastIngestion = issueScheduler.getLastSuccessfulRun() != null
                ? issueScheduler.getLastSuccessfulRun().format(DateTimeFormatter.ISO_LOCAL_DATE)
                : java.time.LocalDate.now(java.time.ZoneOffset.UTC).format(DateTimeFormatter.ISO_LOCAL_DATE);

        return IndexStatsDto.builder()
                .issueCount(statsService.getCachedIssueCount())
                .repositoryCount(statsService.getCachedRepositoryCount())
                .lastIngestionAt(lastIngestion)
                .retrievalBackend("FAISS")
                .schedulerRunning(issueScheduler.isRunning())
                .schedulerFixedRateMs(issueScheduler.getFixedRate())
                .repositoryNames(statsService.getCachedRepositoryNames())
                .build();
    }
}
