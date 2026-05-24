package com.devissueretrieval;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class DevIssueRetrievalApplication {
	public static void main(String[] args) {
		SpringApplication.run(DevIssueRetrievalApplication.class, args);
	}
}

