package com.devissueretrieval.service;

import com.devissueretrieval.model.IndexStatus;
import com.devissueretrieval.repository.IssueRepository;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.concurrent.CompletableFuture;

@Service
@RequiredArgsConstructor
@Slf4j
public class StatsService {

    private final IssueRepository issueRepository;
    private final RetrievalService retrievalService;

    private static final List<String> DEFAULT_REPOSITORIES = List.of(
            "spring-projects/spring-boot",
            "apache/kafka",
            "kubernetes/kubernetes",
            "docker/compose",
            "postgres/postgres"
    );

    private volatile long cachedIssueCount = 5500L;
    private volatile long cachedRepositoryCount = 4L;
    private volatile List<String> cachedRepositoryNames = DEFAULT_REPOSITORIES;

    @PostConstruct
    public void init() {
        log.info("StatsService initialized with in-memory default stats (Issues: {}, Repos: {}). Triggering initial DB refresh...",
                cachedIssueCount, cachedRepositoryCount);
        CompletableFuture.runAsync(this::refreshStats);
    }

    @EventListener(ApplicationReadyEvent.class)
    public void onApplicationReady() {
        CompletableFuture.runAsync(this::refreshStats);
    }

    public synchronized void refreshStats() {
        try {
            long indexedCount = issueRepository.countByIndexStatus(IndexStatus.INDEXED);
            long total = indexedCount > 0 ? indexedCount : retrievalService.getNlpIndexSize();
            if (total <= 0) {
                total = issueRepository.count();
            }

            if (total > 0) {
                this.cachedIssueCount = total;
            }

            List<String> repos = issueRepository.findDistinctRepositoryNames();
            if (repos != null && !repos.isEmpty()) {
                this.cachedRepositoryCount = repos.size();
                this.cachedRepositoryNames = repos;
            }

            log.info("Stats cache successfully refreshed from DB. Issues: {}, Repos: {}", cachedIssueCount, cachedRepositoryCount);
        } catch (Exception ex) {
            log.error("Failed to refresh stats cache from Neon DB. Keeping in-memory values (Issues: {}, Repos: {})",
                    cachedIssueCount, cachedRepositoryCount, ex);
        }
    }

    public long getCachedIssueCount() {
        return cachedIssueCount;
    }

    public long getCachedRepositoryCount() {
        return cachedRepositoryCount;
    }

    public List<String> getCachedRepositoryNames() {
        return cachedRepositoryNames;
    }
}
