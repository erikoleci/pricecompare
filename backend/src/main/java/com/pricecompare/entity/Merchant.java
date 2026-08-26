package com.pricecompare.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/**
 * A store/shop whose offers we crawl and compare.
 * Mirrors db/001_init_schema.sql :: merchants
 */
@Entity
@Table(name = "merchants")
public class Merchant extends PanacheEntityBase {

    @Id
    @GeneratedValue
    public UUID id;

    @Column(nullable = false, length = 150)
    public String name;

    @Column(nullable = false, unique = true, length = 255)
    public String domain;

    @Column(name = "logo_url", length = 500)
    public String logoUrl;

    @Column(length = 2)
    public String country;

    @Column(nullable = false, length = 3)
    public String currency = "EUR";

    public BigDecimal rating;

    @Column(name = "review_count")
    public Integer reviewCount = 0;

    /** ACTIVE, PAUSED, DISABLED, UNSUPPORTED (see spec section 3 - unsupported sources) */
    @Column(nullable = false, length = 20)
    public String status = "ACTIVE";

    @Column(name = "crawler_enabled", nullable = false)
    public boolean crawlerEnabled = false;

    @Column(name = "last_successful_crawl")
    public Instant lastSuccessfulCrawl;

    @Column(name = "created_at", nullable = false)
    public Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    public Instant updatedAt = Instant.now();

    public static Merchant findByDomain(String domain) {
        return find("domain", domain).firstResult();
    }
}
