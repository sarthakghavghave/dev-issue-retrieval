package com.devissueretrieval.repository;

import com.devissueretrieval.model.Issue;
import org.springframework.data.jpa.repository.JpaRepository;

public interface IssueRepository extends JpaRepository<Issue, Long> {
}