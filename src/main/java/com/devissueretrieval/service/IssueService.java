package com.devissueretrieval.service;

import com.devissueretrieval.client.GitHubClient;
import com.devissueretrieval.dto.GitHubIssueDto;
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

    public void fetchAndSaveIssues() {

        List<GitHubIssueDto> githubIssues = gitHubClient.fetchIssues();

        List<Issue> issues = githubIssues.stream()
                .map(dto -> Issue.builder()
                        .githubIssueId(dto.getId())
                        .title(dto.getTitle())
                        .body(dto.getBody())
                        .issueUrl(dto.getHtml_url())
                        .source("github")
                        .repositoryName("spring-boot")
                        .createdAt(dto.getCreated_at())
                        .updatedAt(dto.getUpdated_at())
                        .labels(
                                dto.getLabels() == null
                                        ? ""
                                        : dto.getLabels()
                                        .stream()
                                        .map(GitHubLabelDto::getName)
                                        .reduce((a, b) -> a + "," + b)
                                        .orElse("")
                        )
                        .build())
                .toList();

        issueRepository.saveAll(issues);
    }
}