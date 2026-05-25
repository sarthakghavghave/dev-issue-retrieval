package com.devissueretrieval.service;

import com.devissueretrieval.client.GitHubClient;
import com.devissueretrieval.dto.GitHubIssueDto;
import com.devissueretrieval.dto.GitHubCommentDto;
import com.devissueretrieval.dto.GitHubLabelDto;
import com.devissueretrieval.model.Issue;
import com.devissueretrieval.repository.IssueRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class IssueService {

    private final GitHubClient gitHubClient;
    private final IssueRepository issueRepository;

    private static final List<String> REPOSITORIES = List.of(
            "spring-projects/spring-boot",
            "apache/kafka",
            "kubernetes/kubernetes",
            "docker/compose",
            "postgres/postgres"
    );

    public void fetchIncrementalIssues() {

        for (String repository : REPOSITORIES) {
            List<GitHubIssueDto> githubIssues = gitHubClient.fetchIssues(repository, 1);
            if (githubIssues == null || githubIssues.isEmpty())
                continue;

            for (GitHubIssueDto dto : githubIssues) {
                // only-text or only-body is also acceptable
                if (!isValidIssue(dto))
                    continue;

                // Upsert pattern: update if exists, insert if not
                Issue issue = issueRepository.findByGithubIssueId(dto.getId())
                        .orElse(Issue.builder()
                                .githubIssueId(dto.getId())
                                .source("github")
                                .build());

                boolean isNew = issue.getId() == null;

                // no changes on GitHub since last fetch -> skip
                // If existing, only update when remote `updated_at` is newer than stored `updatedAt`.
                if (!isNew
                        && dto.getUpdated_at() != null
                        && issue.getUpdatedAt() != null
                        && !dto.getUpdated_at().isAfter(issue.getUpdatedAt())) {
                    continue;
                }

                // Update/set fields
                mapIssue(issue, dto, repository);

                issue.setComments(fetchTopComments(dto.getComments_url()));
                issue.setCommentsEnriched(true);

                issueRepository.save(issue);
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

                List<GitHubIssueDto> githubIssues = gitHubClient.fetchIssues(repository, page);
                if (githubIssues == null || githubIssues.isEmpty())
                    break;

                for (GitHubIssueDto dto : githubIssues) {
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

        return comments.stream()
                .limit(3)
                .map(GitHubCommentDto::getBody)
                .filter(comment -> comment != null && !comment.isBlank())
                .reduce((a, b) -> a + "\n\n" + b)
                .orElse("");
    }
}