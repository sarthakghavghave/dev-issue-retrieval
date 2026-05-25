package com.devissueretrieval.client;

import com.devissueretrieval.dto.GitHubIssueDto;
import com.devissueretrieval.dto.GitHubCommentDto;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.RequestEntity;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.net.URI;
import java.util.List;

@Component
@RequiredArgsConstructor
public class GitHubClient {

    @Value("${github.token}")
    private String githubToken;

    private final RestTemplate restTemplate = new RestTemplate();
    private static final List<String> REPOSITORIES = List.of(
            "spring-projects/spring-boot",
            "apache/kafka",
            "kubernetes/kubernetes",
            "docker/compose",
            "postgres/postgres"
    );

    public List<GitHubCommentDto> fetchComments(String commentsUrl) {

        RequestEntity<Void> request = RequestEntity
                .get(URI.create(commentsUrl))
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + githubToken)
                .build();

        return restTemplate.exchange(
                request,
                new ParameterizedTypeReference<List<GitHubCommentDto>>() {}
        ).getBody();
    }

    public List<GitHubIssueDto> fetchIssues(String repository, int page) {

        String url = "https://api.github.com/repos/" + repository + "/issues?state=all&per_page=100&page=" + page;
        // state=all -> open/closed/resolved issues
        // per_page=100 -> GitHub maximum allowed page size

        RequestEntity<Void> request = RequestEntity
                .get(URI.create(url))
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + githubToken)
                .build();

        ResponseEntity<List<GitHubIssueDto>> response =
                restTemplate.exchange(
                        request,
                        new ParameterizedTypeReference<List<GitHubIssueDto>>() {}
                );

        System.out.println("GitHub API Remaining Requests: " + response.getHeaders().getFirst("X-RateLimit-Remaining"));

        return restTemplate.exchange(
                request,
                new ParameterizedTypeReference<List<GitHubIssueDto>>() {}
        ).getBody();
    }
}