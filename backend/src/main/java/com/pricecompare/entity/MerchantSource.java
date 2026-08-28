package com.pricecompare.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/**
 * The compliance review record for one merchant (spec section 3): where the
 * data comes from, whether robots.txt/ToS have been checked, and whether
 * this source is actually approved to crawl. `is_supported` is the single
 * gate `crawler/core/compliance.py` (and any admin UI) should check before
 * ever requesting a page from this merchant.
 * Mirrors db/001_init_schema.sql :: merchant_sources
 */
@Entity
@Table(name = "merchant_sources")
public class MerchantSource extends PanacheEntityBase {

    @Id
    @GeneratedValue
    public UUID id;

    @ManyToOne(optional = false)
    @JoinColumn(name = "merchant_id", nullable = false)
    public Merchant merchant;

    @Column(name = "source_type", nullable = false, length = 20)
    public String sourceType = "SCRAPER"; // SCRAPER, API, XML_FEED, CSV_FEED

    @Column(name = "base_url", nullable = false, length = 500)
    public String baseUrl;

    @Column(name = "robots_txt_url", length = 500)
    public String robotsTxtUrl;

    @Column(name = "robots_txt_checked_at")
    public Instant robotsTxtCheckedAt;

    @Column(name = "allowed_by_robots")
    public Boolean allowedByRobots;

    @Column(name = "tos_reviewed", nullable = false)
    public boolean tosReviewed = false;

    @Column(name = "tos_notes", columnDefinition = "text")
    public String tosNotes;

    @Column(name = "crawl_delay_seconds")
    public BigDecimal crawlDelaySeconds;

    @Column(name = "max_requests_per_min")
    public Integer maxRequestsPerMin;

    /** The single source of truth for "may this be crawled" - false = unsupported (spec section 3). */
    @Column(name = "is_supported", nullable = false)
    public boolean isSupported = false;

    @Column(name = "created_at", nullable = false)
    public Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    public Instant updatedAt = Instant.now();
}
