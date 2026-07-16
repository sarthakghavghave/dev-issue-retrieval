package com.devissueretrieval.dto;

import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class GitHubIssueDto {
    private Long id;
    private String title;
    private String body;
    private String html_url;
    private String comments_url;
    private java.time.Instant created_at;
    private java.time.Instant updated_at;
    private List<GitHubLabelDto> labels;
}