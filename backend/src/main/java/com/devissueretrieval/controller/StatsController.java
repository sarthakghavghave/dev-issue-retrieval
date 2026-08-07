package com.devissueretrieval.controller;

import com.devissueretrieval.dto.IndexStatsDto;
import com.devissueretrieval.model.IndexStatus;
import com.devissueretrieval.repository.IssueRepository;
import com.devissueretrieval.scheduler.IssueScheduler;
import com.devissueretrieval.service.RetrievalService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.format.DateTimeFormatter;

@RestController
@RequestMapping("/api/stats")
@RequiredArgsConstructor
public class StatsController {

    private final IssueRepository issueRepository;
    private final IssueScheduler issueScheduler;
    private final RetrievalService retrievalService;

    @GetMapping
    public IndexStatsDto getStats() {
        long indexedCount = issueRepository.countByIndexStatus(IndexStatus.INDEXED);
        long total = indexedCount > 0 ? indexedCount : retrievalService.getNlpIndexSize();
        if (total <= 0) {
            total = issueRepository.count();
        }
        java.util.List<String> repos = issueRepository.findDistinctRepositoryNames();
        long distinctRepos = repos.size();

        return IndexStatsDto.builder()
                .issueCount(total)
                .repositoryCount(distinctRepos)
                .lastIngestionAt(
                        issueScheduler.getLastSuccessfulRun() == null
                                ? "Never"
                                : issueScheduler.getLastSuccessfulRun()
                                .format(DateTimeFormatter.ISO_LOCAL_DATE)
                )
                .retrievalBackend("FAISS")
                .schedulerRunning(issueScheduler.isRunning())
                .schedulerFixedRateMs(issueScheduler.getFixedRate())
                .repositoryNames(repos)
                .build();
    }
}
