package com.pricecompare.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/**
 * A single merchant's listing/price for a Product.
 * totalPrice = price + shippingCost (shippingCost is null when unknown -
 * NEVER assume free shipping, per spec section 6).
 * Mirrors db/001_init_schema.sql :: offers
 */
@Entity
@Table(name = "offers", uniqueConstraints = @UniqueConstraint(columnNames = {"merchant_id", "merchant_product_id"}))
public class Offer extends PanacheEntityBase {

    @Id
    @GeneratedValue
    public UUID id;

    @ManyToOne(optional = false)
    @JoinColumn(name = "product_id", nullable = false)
    public Product product;

    @ManyToOne(optional = false)
    @JoinColumn(name = "merchant_id", nullable = false)
    public Merchant merchant;

    @Column(name = "merchant_product_id", length = 255)
    public String merchantProductId;

    @Column(nullable = false, precision = 12, scale = 2)
    public BigDecimal price;

    @Column(nullable = false, length = 3)
    public String currency = "EUR";

    @Column(name = "old_price", precision = 12, scale = 2)
    public BigDecimal oldPrice;

    @Column(name = "discount_percent", precision = 5, scale = 2)
    public BigDecimal discountPercent;

    /** null = unknown shipping cost - never default to zero/free */
    @Column(name = "shipping_cost", precision = 12, scale = 2)
    public BigDecimal shippingCost;

    @Column(name = "total_price", nullable = false, precision = 12, scale = 2)
    public BigDecimal totalPrice;

    /** IN_STOCK, OUT_OF_STOCK, PREORDER, UNKNOWN */
    @Column(nullable = false, length = 30)
    public String availability = "UNKNOWN";

    /** NEW, REFURBISHED, USED */
    @Column(nullable = false, length = 20)
    public String condition = "NEW";

    @Column(length = 255)
    public String warranty;

    @Column(nullable = false, length = 700)
    public String url;

    @Column(name = "image_url", length = 700)
    public String imageUrl;

    // --- Provenance (spec section 39) ---
    @Column(name = "source_type", nullable = false, length = 20)
    public String sourceType = "SCRAPER";

    @Column(name = "scraped_at", nullable = false)
    public Instant scrapedAt = Instant.now();

    @Column(name = "last_seen_at", nullable = false)
    public Instant lastSeenAt = Instant.now();

    @Column(name = "last_price_change_at")
    public Instant lastPriceChangeAt;

    @Column(name = "needs_verification", nullable = false)
    public boolean needsVerification = false;

    @Column(name = "created_at", nullable = false)
    public Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    public Instant updatedAt = Instant.now();

    /** Recomputes totalPrice from price + shippingCost (0 only when shipping is explicitly known to be free). */
    public void recalcTotalPrice() {
        this.totalPrice = shippingCost != null ? price.add(shippingCost) : price;
    }
}
