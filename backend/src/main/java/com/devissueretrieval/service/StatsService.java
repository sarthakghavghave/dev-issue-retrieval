package com.devissueretrieval.service;

import com.devissueretrieval.model.IndexStatus;
import com.devissueretrieval.repository.IssueRepository;

import jakarta.annotation.PostConstruct;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class StatsService {

    private final IssueRepository issueRepository;
    private final RetrievalService retrievalService;

    private volatile long cachedIssueCount = 0;
    private volatile long cachedRepositoryCount = 0;
    private volatile List<String> cachedRepositoryNames = Collections.emptyList();

    @PostConstruct
    public void init() {
        log.info("Initializing stats cache on application startup...");
        refreshStats();
    }

    @EventListener(ApplicationReadyEvent.class)
    public void onApplicationReady() {
        if (cachedIssueCount == 0 && cachedRepositoryCount == 0) {
            log.info("Retrying stats cache initialization on ApplicationReadyEvent...");
            refreshStats();
        }
    }

    public synchronized void refreshStats() {
        try {
            long indexedCount = issueRepository.countByIndexStatus(IndexStatus.INDEXED);
            long total = indexedCount > 0 ? indexedCount : retrievalService.getNlpIndexSize();
            if (total <= 0) {
                total = issueRepository.count();
            }

            List<String> repos = issueRepository.findDistinctRepositoryNames();
            if (repos == null) {
                repos = Collections.emptyList();
            }

            this.cachedIssueCount = total;
            this.cachedRepositoryCount = repos.size();
            this.cachedRepositoryNames = repos;

            log.info("Stats cache successfully refreshed. Issues: {}, Repos: {}", total, repos.size());
        } catch (Exception ex) {
            log.error("Failed to refresh stats cache. Keeping previous cached values (Issues: {}, Repos: {})",
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
