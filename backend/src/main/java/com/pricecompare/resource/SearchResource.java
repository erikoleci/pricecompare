package com.pricecompare.resource;

import com.pricecompare.dto.SearchResultDto;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;

import javax.sql.DataSource;
import java.math.BigDecimal;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

/**
 * Search (spec section 23): typo tolerance, brand/model/category detection,
 * EAN/SKU lookup. Uses raw JDBC against the Postgres FTS + pg_trgm setup
 * from db/003_search_and_filters.sql rather than Panache, since neither
 * @@ (tsquery match) nor similarity() have a clean Hibernate/Panache
 * equivalent - this is exactly the kind of query the spec says can start on
 * Postgres FTS and move to OpenSearch later (section 33) without the
 * frontend contract (this DTO) needing to change.
 *
 * Priority, per section 23:
 *   1. Exact EAN/GTIN/MPN/SKU match (barcode/SKU search)
 *   2. Full-text match (title + brand + model + category + specs)
 *   3. Trigram fuzzy fallback when FTS finds nothing (typo tolerance)
 */
@Path("/api/search")
@Produces(MediaType.APPLICATION_JSON)
public class SearchResource {

    @Inject
    DataSource dataSource;

    @GET
    public List<SearchResultDto> search(@QueryParam("q") String rawQuery,
                                         @QueryParam("category") String categorySlug,
                                         @QueryParam("brand") String brandSlug,
                                         @QueryParam("page") @DefaultValue("0") int page,
                                         @QueryParam("size") @DefaultValue("24") int size) throws Exception {
        String q = rawQuery == null ? "" : rawQuery.trim();
        if (q.isEmpty()) {
            return List.of();
        }

        try (Connection conn = dataSource.getConnection()) {
            // 1) identifier lookup - a query that's purely digits (with optional
            // dashes) is almost certainly an EAN/GTIN/SKU/MPN paste, not free text
            if (q.replace("-", "").chars().allMatch(Character::isDigit) && q.length() >= 6) {
                List<SearchResultDto> byIdentifier = searchByIdentifier(conn, q);
                if (!byIdentifier.isEmpty()) {
                    return byIdentifier;
                }
            }

            // 2) full-text search across title/brand/model/category/specs
            List<SearchResultDto> ftsResults = searchFullText(conn, q, categorySlug, brandSlug, page, size);
            if (!ftsResults.isEmpty()) {
                return ftsResults;
            }

            // 3) nothing matched - fall back to trigram similarity so a typo
            // ("plestation" instead of "playstation") still returns something
            return searchFuzzy(conn, q, categorySlug, brandSlug, page, size);
        }
    }

    private List<SearchResultDto> searchByIdentifier(Connection conn, String value) throws Exception {
        String sql = """
                SELECT p.id, p.title, b.name AS brand_name, c.name AS category_name, c.slug AS category_slug,
                       (SELECT MIN(o.total_price) FROM offers o WHERE o.product_id = p.id AND o.availability != 'OUT_OF_STOCK') AS lowest_price,
                       (SELECT COUNT(DISTINCT o.merchant_id) FROM offers o WHERE o.product_id = p.id) AS merchant_count,
                       pi.id_type AS match_id_type
                FROM product_identifiers pi
                JOIN products p ON p.id = pi.product_id
                LEFT JOIN brands b ON b.id = p.brand_id
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE pi.id_value = ? AND p.status = 'ACTIVE'
                """;
        try (PreparedStatement ps = conn.prepareStatement(sql)) {
            ps.setString(1, value);
            return mapResults(ps.executeQuery(), rs -> rs.getString("match_id_type"));
        }
    }

    private List<SearchResultDto> searchFullText(Connection conn, String q, String categorySlug,
                                                  String brandSlug, int page, int size) throws Exception {
        StringBuilder sql = new StringBuilder("""
                SELECT p.id, p.title, b.name AS brand_name, c.name AS category_name, c.slug AS category_slug,
                       (SELECT MIN(o.total_price) FROM offers o WHERE o.product_id = p.id AND o.availability != 'OUT_OF_STOCK') AS lowest_price,
                       (SELECT COUNT(DISTINCT o.merchant_id) FROM offers o WHERE o.product_id = p.id) AS merchant_count,
                       ts_rank(p.search_vector, websearch_to_tsquery('simple', ?)) AS rank
                FROM products p
                LEFT JOIN brands b ON b.id = p.brand_id
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE p.status = 'ACTIVE' AND p.search_vector @@ websearch_to_tsquery('simple', ?)
                """);
        List<Object> params = new ArrayList<>(List.of(q, q));
        appendCategoryAndBrandFilters(sql, params, categorySlug, brandSlug);
        sql.append(" ORDER BY rank DESC LIMIT ? OFFSET ?");
        params.add(size);
        params.add(page * size);

        try (PreparedStatement ps = conn.prepareStatement(sql.toString())) {
            bindParams(ps, params);
            return mapResults(ps.executeQuery(), rs -> "FULLTEXT");
        }
    }

    private List<SearchResultDto> searchFuzzy(Connection conn, String q, String categorySlug,
                                               String brandSlug, int page, int size) throws Exception {
        StringBuilder sql = new StringBuilder("""
                SELECT p.id, p.title, b.name AS brand_name, c.name AS category_name, c.slug AS category_slug,
                       (SELECT MIN(o.total_price) FROM offers o WHERE o.product_id = p.id AND o.availability != 'OUT_OF_STOCK') AS lowest_price,
                       (SELECT COUNT(DISTINCT o.merchant_id) FROM offers o WHERE o.product_id = p.id) AS merchant_count,
                       similarity(p.normalized_title, ?) AS rank
                FROM products p
                LEFT JOIN brands b ON b.id = p.brand_id
                LEFT JOIN categories c ON c.id = p.category_id
                WHERE p.status = 'ACTIVE' AND p.normalized_title % ?
                """);
        List<Object> params = new ArrayList<>(List.of(q.toLowerCase(), q.toLowerCase()));
        appendCategoryAndBrandFilters(sql, params, categorySlug, brandSlug);
        sql.append(" ORDER BY rank DESC LIMIT ? OFFSET ?");
        params.add(size);
        params.add(page * size);

        try (PreparedStatement ps = conn.prepareStatement(sql.toString())) {
            bindParams(ps, params);
            return mapResults(ps.executeQuery(), rs -> "FUZZY");
        }
    }

    private void appendCategoryAndBrandFilters(StringBuilder sql, List<Object> params,
                                                String categorySlug, String brandSlug) {
        if (categorySlug != null && !categorySlug.isBlank()) {
            sql.append(" AND c.slug = ?");
            params.add(categorySlug);
        }
        if (brandSlug != null && !brandSlug.isBlank()) {
            sql.append(" AND b.slug = ?");
            params.add(brandSlug);
        }
    }

    private void bindParams(PreparedStatement ps, List<Object> params) throws Exception {
        for (int i = 0; i < params.size(); i++) {
            ps.setObject(i + 1, params.get(i));
        }
    }

    @FunctionalInterface
    private interface MatchTypeExtractor {
        String extract(ResultSet rs) throws Exception;
    }

    private List<SearchResultDto> mapResults(ResultSet rs, MatchTypeExtractor matchType) throws Exception {
        List<SearchResultDto> results = new ArrayList<>();
        while (rs.next()) {
            UUID productId = UUID.fromString(rs.getString("id"));
            BigDecimal lowest = rs.getBigDecimal("lowest_price"); // null stays null - no offers yet
            results.add(new SearchResultDto(
                    productId,
                    rs.getString("title"),
                    rs.getString("brand_name"),
                    rs.getString("category_name"),
                    rs.getString("category_slug"),
                    lowest,
                    rs.getInt("merchant_count"),
                    matchType.extract(rs)
            ));
        }
        return results;
    }
}
