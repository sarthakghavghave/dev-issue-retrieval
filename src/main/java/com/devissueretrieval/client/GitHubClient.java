package com.devissueretrieval.client;

import com.devissueretrieval.dto.GitHubIssueDto;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpHeaders;
//import org.springframework.http.HttpMethod;
import org.springframework.http.RequestEntity;
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

    public List<GitHubIssueDto> fetchIssues() {

        String url = "https://api.github.com/repos/spring-projects/spring-boot/issues";

        RequestEntity<Void> request = RequestEntity
                .get(URI.create(url))
                .header(HttpHeaders.AUTHORIZATION, "Bearer " + githubToken)
                .build();

        return restTemplate.exchange(
                request,
                new ParameterizedTypeReference<List<GitHubIssueDto>>() {}
        ).getBody();
    }
}