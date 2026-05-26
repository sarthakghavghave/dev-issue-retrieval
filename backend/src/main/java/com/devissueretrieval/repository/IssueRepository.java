package com.devissueretrieval.repository;

import com.devissueretrieval.model.Issue;
import org.springframework.data.jpa.repository.JpaRepository;
import java.util.Optional;

public interface IssueRepository extends JpaRepository<Issue, Long> {
    boolean existsByGithubIssueId(Long githubIssueId);
    Optional<Issue> findByGithubIssueId(Long githubIssueId);
}