package com.pricecompare.entity;

import com.fasterxml.jackson.databind.JsonNode;
import io.quarkus.hibernate.orm.panache.PanacheEntityBase;
import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
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

    /** JSON describing which dynamic filters apply to this category (spec section 24).
     * Mapped as JsonNode (not String) so Jackson serializes this as embedded JSON in API
     * responses - a String field here would come back double-encoded (a JSON string
     * containing escaped JSON text) instead of a real nested object/array. */
    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "filter_schema", columnDefinition = "jsonb")
    public JsonNode filterSchema;
}
