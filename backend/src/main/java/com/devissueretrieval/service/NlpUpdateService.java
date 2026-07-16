package com.devissueretrieval.service;

import com.devissueretrieval.dto.IssueUpdateDto;
import com.devissueretrieval.model.Issue;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestTemplate;

import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.stream.Collectors;

@Service
@Slf4j
public class NlpUpdateService {

    @Value("${retrieval.api.update-url:http://localhost:8000/update-index}")
    private String retrievalApiUpdateUrl;

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;

    public NlpUpdateService(
            ObjectMapper objectMapper,
            @Value("${retrieval.api.update-timeout-ms:120000}") int updateTimeoutMs) {
        this.objectMapper = objectMapper;
        // Configure timeouts so a slow NLP service does not block ingestion forever.
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(10_000);
        factory.setReadTimeout(updateTimeoutMs > 0 ? updateTimeoutMs : 120_000);
        this.restTemplate = new RestTemplate(factory);
    }

    public void updateIssueIndex(List<Issue> issues) {
        if (issues == null || issues.isEmpty()) {
            log.info("No issues to forward to the NLP index update endpoint.");
            return;
        }

        List<IssueUpdateDto> payload = issues.stream()
                .map(this::toDto)
                .collect(Collectors.toList());

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<List<IssueUpdateDto>> request = new HttpEntity<>(payload, headers);

        log.info("Sending {} issues to NLP index update endpoint {}", payload.size(), retrievalApiUpdateUrl);

        try {
            ResponseEntity<String> response = restTemplate.postForEntity(retrievalApiUpdateUrl, request, String.class);

            if (!response.getStatusCode().is2xxSuccessful()) {
                throw new IllegalStateException("Failed to update NLP index: " + response.getStatusCode());
            }

            String body = response.getBody();
            if (body != null) {
                try {
                    JsonNode node = objectMapper.readTree(body);
                    if (node.hasNonNull("status") && "error".equalsIgnoreCase(node.get("status").asText())) {
                        String message = node.hasNonNull("message") ? node.get("message").asText() : body;
                        throw new IllegalStateException("NLP service reported error: " + message);
                    }
                } catch (tools.jackson.core.JacksonException parseEx) {
                    log.debug("NLP index response is not JSON; ignoring: {}", body);
                }
            }

            log.info("NLP index update succeeded: {}", body);
        } catch (HttpStatusCodeException ex) {
            log.error("NLP index update failed with HTTP {}: {}",
                    ex.getStatusCode(), ex.getResponseBodyAsString());
            throw ex;
        } catch (ResourceAccessException ex) {
            log.error("NLP index update timed out / could not reach {}: {}",
                    retrievalApiUpdateUrl, ex.getMessage());
            throw ex;
        } catch (Exception ex) {
            log.error("NLP index update failed for {} issues at {}: {}",
                    payload.size(), retrievalApiUpdateUrl, ex.getMessage());
            throw ex;
        }
    }

    private IssueUpdateDto toDto(Issue issue) {
        return IssueUpdateDto.builder()
                .githubIssueId(issue.getGithubIssueId())
                .repositoryName(issue.getRepositoryName())
                .title(issue.getTitle())
                .body(issue.getBody())
                .labels(issue.getLabels())
                .issueUrl(issue.getIssueUrl())
                .createdAt(issue.getCreatedAt() != null ? issue.getCreatedAt().toString() : "")
                .updatedAt(issue.getUpdatedAt() != null ? issue.getUpdatedAt().toString() : "")
                .comments(issue.getComments())
                .commentsUrl(issue.getCommentsUrl())
                .build();
    }
}
