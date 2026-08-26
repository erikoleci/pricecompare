package com.pricecompare.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.*;
import java.util.UUID;

@Entity
@Table(name = "product_specifications")
public class ProductSpecification extends PanacheEntityBase {
    @Id
    @GeneratedValue
    public UUID id;

    @ManyToOne(optional = false)
    @JoinColumn(name = "product_id", nullable = false)
    public Product product;

    @Column(name = "spec_key", nullable = false, length = 100)
    public String specKey; // e.g. "storage", "ram", "display_size"

    @Column(name = "spec_value", nullable = false, length = 255)
    public String specValue;

    @Column(name = "spec_unit", length = 30)
    public String specUnit;
}
