package com.pricecompare.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.*;
import java.util.UUID;

/** EAN / GTIN / SKU / MPN - used in matching priority order (spec section 15). */
@Entity
@Table(name = "product_identifiers")
public class ProductIdentifier extends PanacheEntityBase {
    @Id
    @GeneratedValue
    public UUID id;

    @ManyToOne(optional = false)
    @JoinColumn(name = "product_id", nullable = false)
    public Product product;

    @Column(name = "id_type", nullable = false, length = 20)
    public String idType; // EAN, GTIN, SKU, MPN

    @Column(name = "id_value", nullable = false, length = 120)
    public String idValue;
}
