package com.pricecompare.resource;

import com.pricecompare.entity.Category;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import java.util.List;

/**
 * Categories + their dynamic filter schemas (spec section 24). The schema
 * itself lives in categories.filter_schema (JSONB, seeded/enriched in
 * db/002_seed_categories_brands.sql and db/003_search_and_filters.sql) -
 * this endpoint just exposes it so the frontend can render the right
 * filter widgets per category without hardcoding them per page.
 */
@Path("/api/categories")
@Produces(MediaType.APPLICATION_JSON)
public class CategoryResource {

    @GET
    public List<Category> list(@QueryParam("topLevelOnly") @DefaultValue("true") boolean topLevelOnly) {
        return topLevelOnly ? Category.list("parent is null") : Category.listAll();
    }

    @GET
    @Path("/{slug}")
    public Category get(@PathParam("slug") String slug) {
        Category c = Category.find("slug", slug).firstResult();
        if (c == null) throw new NotFoundException("Category not found: " + slug);
        return c;
    }
}
