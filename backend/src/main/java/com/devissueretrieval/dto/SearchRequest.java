package com.devissueretrieval.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import lombok.Data;

@Data
@JsonInclude(JsonInclude.Include.NON_NULL)
public class SearchRequest {

    private String query;

    @JsonProperty("top_k")
    private Integer topK;

    @JsonProperty("final_k")
    private Integer finalK;

    @JsonProperty("rerank_k")
    private Integer rerankK;

    @JsonProperty("use_reranker")
    private Boolean useReranker;
}
