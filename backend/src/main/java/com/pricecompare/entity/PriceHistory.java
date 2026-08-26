package com.pricecompare.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/** Append-only record of every price point ever seen for an offer (spec section 8). Never overwritten. */
@Entity
@Table(name = "price_history")
public class PriceHistory extends PanacheEntityBase {
    @Id
    @GeneratedValue
    public UUID id;

    @ManyToOne(optional = false)
    @JoinColumn(name = "product_id", nullable = false)
    public Product product;

    @ManyToOne(optional = false)
    @JoinColumn(name = "offer_id", nullable = false)
    public Offer offer;

    @ManyToOne(optional = false)
    @JoinColumn(name = "merchant_id", nullable = false)
    public Merchant merchant;

    @Column(nullable = false, precision = 12, scale = 2)
    public BigDecimal price;

    @Column(name = "shipping_cost", precision = 12, scale = 2)
    public BigDecimal shippingCost;

    @Column(name = "total_price", nullable = false, precision = 12, scale = 2)
    public BigDecimal totalPrice;

    @Column(nullable = false, length = 3)
    public String currency = "EUR";

    @Column(nullable = false, length = 30)
    public String availability = "UNKNOWN";

    @Column(name = "recorded_at", nullable = false)
    public Instant recordedAt = Instant.now();
}
