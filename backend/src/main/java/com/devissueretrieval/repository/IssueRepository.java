package com.devissueretrieval.repository;

import com.devissueretrieval.model.Issue;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import java.util.Optional;

public interface IssueRepository extends JpaRepository<Issue, Long> {
    boolean existsByGithubIssueId(Long githubIssueId);
    Optional<Issue> findByGithubIssueId(Long githubIssueId);
    Optional<Issue> findTopByRepositoryNameOrderByUpdatedAtDesc(String repositoryName);

    @Query("SELECT COUNT(DISTINCT i.repositoryName) FROM Issue i WHERE i.repositoryName IS NOT NULL AND i.repositoryName <> ''")
    long countDistinctRepositoryNames();

    @Query("SELECT DISTINCT i.repositoryName FROM Issue i WHERE i.repositoryName IS NOT NULL AND i.repositoryName <> '' ORDER BY i.repositoryName")
    java.util.List<String> findDistinctRepositoryNames();
}