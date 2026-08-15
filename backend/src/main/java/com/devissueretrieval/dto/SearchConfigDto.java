package com.devissueretrieval.dto;

import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
public class SearchConfigDto {

    @JsonProperty("top_k")
    private int topK;

    @JsonProperty("final_k")
    private int finalK;

    @JsonProperty("rerank_k")
    private int rerankK;

    @JsonProperty("use_reranker")
    private boolean useReranker;
}
