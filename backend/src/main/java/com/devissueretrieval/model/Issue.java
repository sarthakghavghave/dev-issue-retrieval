package com.devissueretrieval.model;

import com.devissueretrieval.model.IndexStatus;
import com.devissueretrieval.model.FilterReason;

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

    @Column(columnDefinition = "TEXT")
    private String title;

    @Column(columnDefinition = "TEXT")
    private String body;

    @Column(columnDefinition = "TEXT")
    private String comments;

    @Column(columnDefinition = "TEXT")
    private String commentsUrl;
    private Boolean commentsEnriched;

    private String repositoryName;

    @Column(columnDefinition = "TEXT")
    private String issueUrl;

    @Column(columnDefinition = "TEXT")
    private String labels;
    private String source;

    private java.time.Instant createdAt;
    private java.time.Instant updatedAt;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    @Builder.Default
    private IndexStatus indexStatus = IndexStatus.PENDING;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    @Builder.Default
    private FilterReason filterReason = FilterReason.NONE;
}