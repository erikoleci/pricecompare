package com.pricecompare.dto;

import java.time.Instant;
import java.util.UUID;

/** One row of the admin merchants table - merchant + its compliance review state. */
public class AdminMerchantDto {
    public UUID merchantId;
    public String name;
    public String domain;
    public String status;
    public boolean crawlerEnabled;
    public Instant lastSuccessfulCrawl;

    // compliance (spec section 3) - null fields mean "no merchant_sources row yet"
    public UUID sourceId;
    public String sourceType;
    public String baseUrl;
    public String robotsTxtUrl;
    public Instant robotsTxtCheckedAt;
    public Boolean allowedByRobots;
    public boolean tosReviewed;
    public String tosNotes;
    public boolean isSupported;

    public AdminMerchantDto(UUID merchantId, String name, String domain, String status,
                             boolean crawlerEnabled, Instant lastSuccessfulCrawl,
                             UUID sourceId, String sourceType, String baseUrl, String robotsTxtUrl,
                             Instant robotsTxtCheckedAt, Boolean allowedByRobots, boolean tosReviewed,
                             String tosNotes, boolean isSupported) {
        this.merchantId = merchantId;
        this.name = name;
        this.domain = domain;
        this.status = status;
        this.crawlerEnabled = crawlerEnabled;
        this.lastSuccessfulCrawl = lastSuccessfulCrawl;
        this.sourceId = sourceId;
        this.sourceType = sourceType;
        this.baseUrl = baseUrl;
        this.robotsTxtUrl = robotsTxtUrl;
        this.robotsTxtCheckedAt = robotsTxtCheckedAt;
        this.allowedByRobots = allowedByRobots;
        this.tosReviewed = tosReviewed;
        this.tosNotes = tosNotes;
        this.isSupported = isSupported;
    }
}
