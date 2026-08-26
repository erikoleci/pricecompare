package com.pricecompare.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.*;
import java.time.Instant;
import java.util.List;
import java.util.UUID;

/**
 * A canonical product, deduplicated across merchants by the matcher.
 * Mirrors db/001_init_schema.sql :: products
 */
@Entity
@Table(name = "products")
public class Product extends PanacheEntityBase {

    @Id
    @GeneratedValue
    public UUID id;

    @ManyToOne
    @JoinColumn(name = "brand_id")
    public Brand brand;

    @ManyToOne
    @JoinColumn(name = "category_id")
    public Category category;

    @ManyToOne
    @JoinColumn(name = "subcategory_id")
    public Category subcategory;

    @Column(length = 255)
    public String model;

    @Column(nullable = false, length = 500)
    public String title;

    @Column(name = "normalized_title", nullable = false, length = 500)
    public String normalizedTitle;

    @Column(columnDefinition = "text")
    public String description;

    /** ACTIVE, MERGED, NEEDS_REVIEW, REMOVED */
    @Column(nullable = false, length = 20)
    public String status = "ACTIVE";

    @Column(name = "created_at", nullable = false)
    public Instant createdAt = Instant.now();

    @Column(name = "updated_at", nullable = false)
    public Instant updatedAt = Instant.now();

    @OneToMany(mappedBy = "product", cascade = CascadeType.ALL, orphanRemoval = true)
    public List<ProductIdentifier> identifiers;

    @OneToMany(mappedBy = "product", cascade = CascadeType.ALL, orphanRemoval = true)
    public List<ProductSpecification> specifications;

    @OneToMany(mappedBy = "product", cascade = CascadeType.ALL, orphanRemoval = true)
    public List<Offer> offers;
}
