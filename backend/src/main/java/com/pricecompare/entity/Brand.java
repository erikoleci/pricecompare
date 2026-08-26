package com.pricecompare.entity;

import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.*;
import java.util.UUID;

@Entity
@Table(name = "brands")
public class Brand extends PanacheEntityBase {
    @Id
    @GeneratedValue
    public UUID id;

    @Column(nullable = false, unique = true, length = 150)
    public String slug;

    @Column(nullable = false, length = 150)
    public String name;

    @Column(name = "logo_url", length = 500)
    public String logoUrl;
}
