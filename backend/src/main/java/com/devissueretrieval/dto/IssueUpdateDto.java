package com.devissueretrieval.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class IssueUpdateDto {

    @JsonProperty("github_issue_id")
    private Long githubIssueId;

    @JsonProperty("repository_name")
    private String repositoryName;

    private String title;
    private String body;
    private String labels;

    @JsonProperty("issue_url")
    private String issueUrl;

    @JsonProperty("created_at")
    private String createdAt;

    private String comments;

    @JsonProperty("updated_at")
    private String updatedAt;

    @JsonProperty("comments_url")
    private String commentsUrl;
}
