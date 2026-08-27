package com.pricecompare.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.UUID;

/**
 * Aggregate rating rollup for a product (spec section 17) - never generated,
 * only computed from real reviews once a permitted source provides them
 * (spec section 16/40: no fake reviews, no fake ratings).
 * Mirrors db/001_init_schema.sql :: review_summary (product_id is both PK and FK).
 */
@Entity
@Table(name = "review_summary")
public class ReviewSummary extends PanacheEntityBase {

    @Id
    @Column(name = "product_id")
    public UUID productId;

    @OneToOne
    @MapsId
    @JoinColumn(name = "product_id")
    public Product product;

    @Column(name = "average_rating", precision = 3, scale = 2)
    public java.math.BigDecimal averageRating;

    @Column(name = "review_count", nullable = false)
    public int reviewCount = 0;

    /** e.g. {"5": 72, "4": 18, "3": 6, "2": 2, "1": 2} - percentages, spec section 16 */
    @Column(name = "rating_distribution", columnDefinition = "jsonb")
    public String ratingDistribution;

    @Column(name = "updated_at", nullable = false)
    public Instant updatedAt = Instant.now();
}
