package com.devissueretrieval.model;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "issues")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Issue {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(unique = true)
    private Long githubIssueId;
    private String title;

    @Column(columnDefinition = "TEXT")
    private String body;

    @Column(columnDefinition = "TEXT")
    private String comments;
    private String repositoryName;
    private String issueUrl;

    @Column(columnDefinition = "TEXT")
    private String labels;
    private String source;

    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}