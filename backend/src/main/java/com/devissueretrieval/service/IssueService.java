package com.devissueretrieval.service;

import com.devissueretrieval.client.GitHubClient;
import com.devissueretrieval.dto.GitHubIssueDto;
import com.devissueretrieval.dto.GitHubCommentDto;
import com.devissueretrieval.dto.GitHubLabelDto;
import com.devissueretrieval.model.Issue;
import com.devissueretrieval.repository.IssueRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
@Slf4j
public class IssueService {

    private final GitHubClient gitHubClient;
    private final IssueRepository issueRepository;
    private final NlpUpdateService nlpUpdateService;
    int repositoriesProcessed = 0;

    private static final List<String> REPOSITORIES = List.of(
            "spring-projects/spring-boot",
            "apache/kafka",
            "kubernetes/kubernetes",
            "docker/compose",
            "postgres/postgres"
    );

    private static final int GITHUB_MAX_PAGES = 5; // 5 * 100 = up to 500 newest updates per repo per run

    public void fetchIncrementalIssues() {

        List<Issue> changedIssues = new ArrayList<>();

        for (String repository : REPOSITORIES) {
            try {
                processRepository(repository, changedIssues);
                repositoriesProcessed++;
            } catch (Exception ex) {
                // A failure on one repository must not stop ingestion for the others.
                log.error("Incremental ingestion failed for repository {}", repository, ex);
            }
        }

        log.info("Changed issues count: {}", changedIssues.size());

        if (!changedIssues.isEmpty()) {
            try {
                log.info("Incremental ingestion summary");
                log.info("Repositories processed : {}", repositoriesProcessed);
                log.info("Changed issues         : {}", changedIssues.size());
                nlpUpdateService.updateIssueIndex(changedIssues);
            } catch (Exception ex) {
                log.error("Failed to update NLP index after ingesting issues", ex);
            }
        }
    }

    private void processRepository(String repository, List<Issue> changedIssues) {

        java.time.Instant latestUpdate = issueRepository.findTopByRepositoryNameOrderByUpdatedAtDesc(repository)
                .map(Issue::getUpdatedAt)
                .orElse(java.time.Instant.now().minus(java.time.Duration.ofDays(1)));

        String since = latestUpdate
                .plus(java.time.Duration.ofSeconds(1))
                .toString();

        log.info("Fetching {} since {} (latest DB updated_at = {})", repository, since, latestUpdate);

        boolean keepPaging = true;
        for (int page = 1; page <= GITHUB_MAX_PAGES && keepPaging; page++) {

            List<GitHubIssueDto> githubIssues;
            try {
                githubIssues = gitHubClient.fetchIssues(repository, page, since);
            } catch (Exception ex) {
                log.error("GitHub API call failed for {} (page {}): {}", repository, page, ex.getMessage());
                return;
            }

            log.info("Repository {} page {} returned {} issues", repository, page,
                    githubIssues == null ? 0 : githubIssues.size());

            if (githubIssues == null || githubIssues.isEmpty()) {
                return;
            }

            int processedThisPage = 0;
            for (GitHubIssueDto dto : githubIssues) {

                // GitHub returns pull requests as issues too; skip those.
                if (dto.getId() == null) {
                    continue;
                }

                // once we see an issue whose `updated_at` is older than the watermark
                // we already have, we know every later one is also older -> stop paging.
                if (dto.getUpdated_at() != null
                        && latestUpdate != null
                        && !dto.getUpdated_at().isAfter(latestUpdate)) {
                    keepPaging = false;
                    break;
                }

                if (!isValidIssue(dto)) {
                    continue;
                }

                Issue issue = issueRepository.findByGithubIssueId(dto.getId())
                        .orElse(Issue.builder()
                                .githubIssueId(dto.getId())
                                .source("github")
                                .build());

                boolean isNew = issue.getId() == null;

                if (!isNew
                        && dto.getUpdated_at() != null
                        && issue.getUpdatedAt() != null
                        && !dto.getUpdated_at().isAfter(issue.getUpdatedAt())) {
                    continue;
                }

                mapIssue(issue, dto, repository);

                try {
                    issue.setComments(fetchTopComments(dto.getComments_url()));
                    issue.setCommentsEnriched(true);
                } catch (Exception ex) {
                    // If the comments endpoint fails, we still want to keep the issue
                    // update - just persist it with no comments for now.
                    log.warn("Could not fetch comments for issue {}: {}", dto.getId(), ex.getMessage());
                    issue.setComments("");
                    issue.setCommentsEnriched(false);
                }

                Issue saved = issueRepository.save(issue);
                changedIssues.add(saved);
                processedThisPage++;
            }

            log.info("Repository {} page {} processed {} changed issues", repository, page, processedThisPage);

            try {
                Thread.sleep(800);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }

    public void fetchHistoricalIssues() {

        for (String repository : REPOSITORIES) {
            for (int page = 1; page <= 20; page++) {

                try {
                    Thread.sleep(1000);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }

                List<GitHubIssueDto> githubIssues;
                try {
                    githubIssues = gitHubClient.fetchIssues(repository, page);
                } catch (Exception ex) {
                    log.error("Historical backfill failed for {} (page {}): {}",
                            repository, page, ex.getMessage());
                    break;
                }
                if (githubIssues == null || githubIssues.isEmpty())
                    break;

                for (GitHubIssueDto dto : githubIssues) {
                    if (dto.getId() == null) {
                        continue;
                    }
                    if (!isValidIssue(dto))
                        continue;

                    boolean exists = issueRepository.existsByGithubIssueId(dto.getId());
                    if (exists)
                        continue;

                    Issue issue = Issue.builder()
                            .githubIssueId(dto.getId())
                            .source("github")
                            .build();

                    mapIssue(issue, dto, repository);

                    issue.setComments("");
                    issue.setCommentsEnriched(false);

                    issueRepository.save(issue);
                }
            }
        }
    }

    private boolean isValidIssue(GitHubIssueDto dto) {
        return (dto.getTitle() != null && !dto.getTitle().isBlank())
                || (dto.getBody() != null && !dto.getBody().isBlank());
    }

    private void mapIssue(Issue issue, GitHubIssueDto dto, String repository) {

        issue.setTitle(dto.getTitle());
        issue.setBody(dto.getBody());
        issue.setIssueUrl(dto.getHtml_url());

        issue.setRepositoryName(repository);

        issue.setCreatedAt(dto.getCreated_at());
        issue.setUpdatedAt(dto.getUpdated_at());

        issue.setCommentsUrl(dto.getComments_url());

        issue.setLabels(
                dto.getLabels() == null
                        ? ""
                        : dto.getLabels()
                        .stream()
                        .map(GitHubLabelDto::getName)
                        .reduce((a, b) -> a + "," + b)
                        .orElse("")
        );
    }

    private String fetchTopComments(String commentsUrl) {
        if (commentsUrl == null)
            return "";
        List<GitHubCommentDto> comments = gitHubClient.fetchComments(commentsUrl);
        if (comments == null)
            return "";

        return comments.stream()
                .limit(3)
                .map(GitHubCommentDto::getBody)
                .filter(comment -> comment != null && !comment.isBlank())
                .reduce((a, b) -> a + "\n\n" + b)
                .orElse("");
    }
}