package com.devissueretrieval.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class IndexStatsDto {
    private long issueCount;
    private long repositoryCount;
    private String lastIngestionAt;
    private String retrievalBackend;
    private boolean schedulerRunning;
    private long schedulerFixedRateMs;
}
