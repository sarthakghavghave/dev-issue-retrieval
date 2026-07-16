package com.devissueretrieval.client;

import com.devissueretrieval.dto.GitHubIssueDto;
import com.devissueretrieval.dto.GitHubCommentDto;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.RequestEntity;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestTemplate;

import java.net.URI;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.List;

@Component
@RequiredArgsConstructor
@Slf4j
public class GitHubClient {

    @Value("${github.token:dummy}")
    private String githubToken;

    private final RestTemplate restTemplate = new RestTemplate();

    public List<GitHubCommentDto> fetchComments(String commentsUrl) {

        if (commentsUrl == null || commentsUrl.isBlank()) {
            return Collections.emptyList();
        }

        RequestEntity<Void> request = RequestEntity
                .get(URI.create(commentsUrl))
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + githubToken)
                .header(HttpHeaders.ACCEPT, "application/vnd.github+json")
                .build();

        try {
            return restTemplate.exchange(
                    request,
                    new ParameterizedTypeReference<List<GitHubCommentDto>>() {}
            ).getBody();
        } catch (HttpStatusCodeException ex) {
            log.warn("Comments fetch failed ({}): {}", ex.getStatusCode(), ex.getMessage());
            return Collections.emptyList();
        }
    }

    public List<GitHubIssueDto> fetchIssues(String repository, int page, String since) {

        String url = "https://api.github.com/repos/" + repository
                + "/issues?state=all&per_page=100&page=" + page
                + "&sort=updated&direction=desc";
        // state=all -> open/closed/resolved issues
        // per_page=100 -> GitHub maximum allowed page size
        // sort=updated -> most recently updated issues first

        if (since != null && !since.isBlank()) {
            url += "&since=" + URLEncoder.encode(since, StandardCharsets.UTF_8);
        }

        RequestEntity<Void> request = RequestEntity
                .get(URI.create(url))
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + githubToken)
                .header(HttpHeaders.ACCEPT, "application/vnd.github+json")
                .build();

        try {
            ResponseEntity<List<GitHubIssueDto>> response =
                    restTemplate.exchange(
                            request,
                            new ParameterizedTypeReference<List<GitHubIssueDto>>() {}
                    );

            log.debug("GitHub API Remaining Requests: {}",
                    response.getHeaders().getFirst("X-RateLimit-Remaining"));

            return response.getBody();
        } catch (HttpStatusCodeException ex) {
            if (ex.getStatusCode() == HttpStatus.NOT_MODIFIED) {
                // 304 means: nothing has changed since our `since` watermark.
                return Collections.emptyList();
            }
            if (ex.getStatusCode() == HttpStatus.FORBIDDEN || ex.getStatusCode() == HttpStatus.TOO_MANY_REQUESTS) {
                log.error("GitHub API rate limit / auth issue for {}: {}",
                        repository, ex.getStatusCode());
            } else {
                log.error("GitHub API call failed for {} (page {}): {} {}",
                        repository, page, ex.getStatusCode(), ex.getMessage());
            }
            throw ex;
        }
    }

    public List<GitHubIssueDto> fetchIssues(String repository, int page) {
        return fetchIssues(repository, page, null);
    }
}