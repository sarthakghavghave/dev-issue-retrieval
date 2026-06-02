package com.devissueretrieval.controller;

import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;

@Controller
public class SearchPageController {

    @GetMapping("/")
    public String home() {
        return "search";
    }

    @GetMapping("/architecture")
    public String architecture() {
        return "architecture";
    }
}