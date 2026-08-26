package com.pricecompare.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.*;
import java.util.UUID;

@Entity
@Table(name = "categories")
public class Category extends PanacheEntityBase {
    @Id
    @GeneratedValue
    public UUID id;

    @ManyToOne
    @JoinColumn(name = "parent_id")
    public Category parent;

    @Column(nullable = false, unique = true, length = 150)
    public String slug;

    @Column(nullable = false, length = 150)
    public String name;

    /** JSON describing which dynamic filters apply to this category (spec section 24) */
    @Column(name = "filter_schema", columnDefinition = "jsonb")
    public String filterSchema;
}
