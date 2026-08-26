package com.pricecompare.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

/** One execution of a crawler_job for a merchant (spec section 29). */
@Entity
@Table(name = "crawler_runs")
public class CrawlerRun extends PanacheEntityBase {
    @Id
    @GeneratedValue
    public UUID id;

    @Column(name = "crawler_job_id", nullable = false)
    public UUID crawlerJobId;

    @ManyToOne(optional = false)
    @JoinColumn(name = "merchant_id", nullable = false)
    public Merchant merchant;

    /** RUNNING, SUCCESS, FAILED, PARTIAL */
    @Column(nullable = false, length = 20)
    public String status = "RUNNING";

    @Column(name = "products_found")
    public Integer productsFound = 0;
    @Column(name = "products_updated")
    public Integer productsUpdated = 0;
    @Column(name = "prices_changed")
    public Integer pricesChanged = 0;
    @Column(name = "new_products")
    public Integer newProducts = 0;
    @Column(name = "out_of_stock")
    public Integer outOfStock = 0;

    @Column(name = "started_at", nullable = false)
    public Instant startedAt = Instant.now();

    @Column(name = "finished_at")
    public Instant finishedAt;

    @Column(name = "duration_ms")
    public Integer durationMs;
}
