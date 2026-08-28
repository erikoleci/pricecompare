package com.pricecompare.resource;

import com.pricecompare.dto.AdminMerchantDto;
import com.pricecompare.dto.ComplianceReviewRequest;
import com.pricecompare.entity.Merchant;
import com.pricecompare.entity.MerchantSource;
import com.pricecompare.entity.Offer;
import com.pricecompare.entity.Product;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import java.time.Instant;
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
}
