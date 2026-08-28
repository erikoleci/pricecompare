package com.pricecompare.resource;

import com.pricecompare.dto.AdminMerchantDto;
import com.pricecompare.dto.ComplianceReviewRequest;
import com.pricecompare.entity.Merchant;
import com.pricecompare.entity.MerchantSource;
import com.pricecompare.entity.Offer;
import com.pricecompare.entity.Product;
import jakarta.inject.Inject;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.ResultSetMetaData;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * Admin dashboard backend (spec sections 3, 7, 28). Merchant management is
 * the part directly tied to spec section 3's compliance requirement: this
 * is where a human records that they actually read robots.txt and the ToS
 * for a merchant, and only that action - never a crawl attempt itself - can
 * set is_supported=true. Everything here is the same workflow this
 * project's chat sessions did by hand with SQL migrations
 * (db/004-007_*.sql); this gives it a real UI instead.
 */
@Path("/api/admin")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class AdminResource {

    @Inject
    DataSource dataSource;

    @GET
    @Path("/merchants")
    public List<AdminMerchantDto> listMerchants() {
        List<Merchant> merchants = Merchant.listAll();
        return merchants.stream().map(m -> {
            MerchantSource source = MerchantSource.find("merchant = ?1", m).firstResult();
            return new AdminMerchantDto(
                    m.id, m.name, m.domain, m.status, m.crawlerEnabled, m.lastSuccessfulCrawl,
                    source != null ? source.id : null,
                    source != null ? source.sourceType : null,
                    source != null ? source.baseUrl : null,
                    source != null ? source.robotsTxtUrl : null,
                    source != null ? source.robotsTxtCheckedAt : null,
                    source != null ? source.allowedByRobots : null,
                    source != null && source.tosReviewed,
                    source != null ? source.tosNotes : null,
                    source != null && source.isSupported
            );
        }).collect(Collectors.toList());
    }

    /**
     * Record a real robots.txt/ToS review (spec section 3). `approve` only takes
     * effect when both allowedByRobots and tosReviewed end up true - this endpoint
     * refuses to let is_supported flip to true off a partial or negative review,
     * since that's exactly the shortcut section 3 exists to prevent.
     */
    @PATCH
    @Path("/merchants/{id}/compliance")
    @Transactional
    public AdminMerchantDto updateCompliance(@PathParam("id") UUID merchantId, ComplianceReviewRequest body) {
        Merchant merchant = Merchant.findById(merchantId);
        if (merchant == null) throw new NotFoundException("Merchant not found: " + merchantId);

        MerchantSource source = MerchantSource.find("merchant = ?1", merchant).firstResult();
        if (source == null) {
            source = new MerchantSource();
            source.merchant = merchant;
            source.baseUrl = "https://" + merchant.domain + "/";
            source.robotsTxtUrl = "https://" + merchant.domain + "/robots.txt";
        }

        if (body.allowedByRobots != null) {
            source.allowedByRobots = body.allowedByRobots;
            source.robotsTxtCheckedAt = Instant.now();
        }
        if (body.tosReviewed != null) source.tosReviewed = body.tosReviewed;
        if (body.tosNotes != null) source.tosNotes = body.tosNotes;

        boolean canApprove = Boolean.TRUE.equals(source.allowedByRobots) && source.tosReviewed;
        if (Boolean.TRUE.equals(body.approve)) {
            if (!canApprove) {
                throw new BadRequestException(
                        "Cannot approve: needs allowedByRobots=true AND tosReviewed=true first (spec section 3)");
            }
            source.isSupported = true;
            merchant.status = "ACTIVE";
        } else if (Boolean.FALSE.equals(body.approve)) {
            source.isSupported = false;
            merchant.crawlerEnabled = false;
        }

        source.updatedAt = Instant.now();
        source.persist();
        merchant.updatedAt = Instant.now();
        merchant.persist();

        return new AdminMerchantDto(
                merchant.id, merchant.name, merchant.domain, merchant.status, merchant.crawlerEnabled,
                merchant.lastSuccessfulCrawl, source.id, source.sourceType, source.baseUrl, source.robotsTxtUrl,
                source.robotsTxtCheckedAt, source.allowedByRobots, source.tosReviewed, source.tosNotes,
                source.isSupported
        );
    }

    /** Dashboard rollup (spec section 28) - catalog-wide counts, not crawler-run-specific
     * (those live in CrawlerMonitoringResource's /api/admin/crawler/summary). */
    @GET
    @Path("/dashboard")
    public Map<String, Object> dashboard() {
        long totalProducts = Product.count();
        long activeProducts = Product.count("status = 'ACTIVE'");
        long totalOffers = Offer.count();
        long totalMerchants = Merchant.count();
        long activeMerchants = Merchant.count("status = 'ACTIVE'");
        long unsupportedMerchants = Merchant.count("status = 'UNSUPPORTED'");
        long approvedSources = MerchantSource.count("isSupported = true");
        long pendingSources = MerchantSource.count("isSupported = false");

        return Map.of(
                "totalProducts", totalProducts,
                "activeProducts", activeProducts,
                "totalOffers", totalOffers,
                "totalMerchants", totalMerchants,
                "activeMerchants", activeMerchants,
                "unsupportedMerchants", unsupportedMerchants,
                "approvedSources", approvedSources,
                "pendingComplianceReview", pendingSources
        );
    }

    // ------------------------------------------------------------------
    // Remaining spec-section-28 dashboard sections: Products, Offers,
    // Reviews, Price Drops, Price Alerts, Searches, Clicks. Products/Offers
    // already have Panache entities; the rest don't yet (they were never
    // needed outside the crawler's write path until now), so these use raw
    // JDBC the same way SearchResource does, returning plain maps rather
    // than adding five more DTO classes for what's fundamentally a
    // read-only admin table view. Every row here reflects only what
    // actually happened (real searches, real clicks, real price drops
    // detected by the crawler) - nothing here is ever synthesized (spec
    // section 40).
    // ------------------------------------------------------------------

    @GET
    @Path("/products")
    public List<Product> listProducts(@QueryParam("page") @DefaultValue("0") int page,
                                       @QueryParam("size") @DefaultValue("50") int size) {
        return Product.findAll().page(page, size).list();
    }

    @GET
    @Path("/offers")
    public List<Offer> listOffers(@QueryParam("page") @DefaultValue("0") int page,
                                   @QueryParam("size") @DefaultValue("50") int size) {
        return Offer.findAll().page(page, size).list();
    }

    @GET
    @Path("/reviews")
    public List<Map<String, Object>> listReviews(@QueryParam("page") @DefaultValue("0") int page,
                                                  @QueryParam("size") @DefaultValue("50") int size) throws Exception {
        return rawQuery("""
                SELECT r.id, r.product_id, p.title AS product_title, r.source, r.author_name,
                       r.rating, r.title, r.verified, r.review_date
                FROM reviews r JOIN products p ON p.id = r.product_id
                ORDER BY r.created_at DESC LIMIT ? OFFSET ?
                """, size, page * size);
    }

    @GET
    @Path("/price-drops")
    public List<Map<String, Object>> listPriceDrops(@QueryParam("page") @DefaultValue("0") int page,
                                                     @QueryParam("size") @DefaultValue("50") int size) throws Exception {
        return rawQuery("""
                SELECT pde.id, p.title AS product_title, m.name AS merchant_name,
                       pde.old_price, pde.new_price, pde.drop_percent, pde.drop_amount, pde.detected_at
                FROM price_drop_events pde
                JOIN products p ON p.id = pde.product_id
                JOIN merchants m ON m.id = pde.merchant_id
                ORDER BY pde.detected_at DESC LIMIT ? OFFSET ?
                """, size, page * size);
    }

    @GET
    @Path("/price-alerts")
    public List<Map<String, Object>> listPriceAlerts(@QueryParam("page") @DefaultValue("0") int page,
                                                      @QueryParam("size") @DefaultValue("50") int size) throws Exception {
        return rawQuery("""
                SELECT pa.id, p.title AS product_title, pa.target_price, pa.active, pa.triggered_at, pa.created_at
                FROM price_alerts pa JOIN products p ON p.id = pa.product_id
                ORDER BY pa.created_at DESC LIMIT ? OFFSET ?
                """, size, page * size);
    }

    @GET
    @Path("/searches")
    public List<Map<String, Object>> listSearches(@QueryParam("page") @DefaultValue("0") int page,
                                                   @QueryParam("size") @DefaultValue("50") int size) throws Exception {
        return rawQuery("""
                SELECT id, query, result_count, created_at
                FROM search_history ORDER BY created_at DESC LIMIT ? OFFSET ?
                """, size, page * size);
    }

    @GET
    @Path("/clicks")
    public List<Map<String, Object>> listClicks(@QueryParam("page") @DefaultValue("0") int page,
                                                 @QueryParam("size") @DefaultValue("50") int size) throws Exception {
        return rawQuery("""
                SELECT ce.id, p.title AS product_title, ce.event_type, ce.created_at
                FROM click_events ce LEFT JOIN products p ON p.id = ce.product_id
                ORDER BY ce.created_at DESC LIMIT ? OFFSET ?
                """, size, page * size);
    }

    private List<Map<String, Object>> rawQuery(String sql, Object... params) throws Exception {
        try (Connection conn = dataSource.getConnection(); PreparedStatement ps = conn.prepareStatement(sql)) {
            for (int i = 0; i < params.length; i++) ps.setObject(i + 1, params[i]);
            try (ResultSet rs = ps.executeQuery()) {
                ResultSetMetaData meta = rs.getMetaData();
                List<Map<String, Object>> rows = new ArrayList<>();
                while (rs.next()) {
                    Map<String, Object> row = new LinkedHashMap<>();
                    for (int i = 1; i <= meta.getColumnCount(); i++) {
                        row.put(meta.getColumnLabel(i), rs.getObject(i));
                    }
                    rows.add(row);
                }
                return rows;
            }
        }
    }
}
