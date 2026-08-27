package com.pricecompare.resource;

import com.pricecompare.dto.CompareProductDto;
import com.pricecompare.dto.OfferDto;
import com.pricecompare.entity.Offer;
import com.pricecompare.entity.PriceHistory;
import com.pricecompare.entity.Product;
import com.pricecompare.entity.ProductSpecification;
import com.pricecompare.entity.ReviewSummary;
import com.pricecompare.service.PriceAnalyticsService;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import java.math.BigDecimal;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.stream.Collectors;

@Path("/api/products")
@Produces(MediaType.APPLICATION_JSON)
public class ProductResource {

    @Inject
    PriceAnalyticsService analytics;

    @GET
    public List<Product> list(@QueryParam("category") String categorySlug,
                               @QueryParam("brand") String brandSlug,
                               @QueryParam("page") @DefaultValue("0") int page,
                               @QueryParam("size") @DefaultValue("24") int size) {
        StringBuilder query = new StringBuilder("status = 'ACTIVE'");
        List<Object> params = new java.util.ArrayList<>();
        if (categorySlug != null && !categorySlug.isBlank()) {
            query.append(" and category.slug = ?").append(params.size() + 1);
            params.add(categorySlug);
        }
        if (brandSlug != null && !brandSlug.isBlank()) {
            query.append(" and brand.slug = ?").append(params.size() + 1);
            params.add(brandSlug);
        }
        return Product.find(query.toString(), params.toArray()).page(page, size).list();
        // NOTE: dynamic per-category filter VALUES (spec section 24, e.g. "Storage: 256GB")
        // still need a facet-count query once enough real offers exist to facet over;
        // the filter *schema* itself is served by CategoryResource.
    }

    @GET
    @Path("/{id}")
    public Product get(@PathParam("id") UUID id) {
        Product p = Product.findById(id);
        if (p == null) throw new NotFoundException("Product not found: " + id);
        return p;
    }

    /**
     * Cheapest -> most expensive offer list for a product (spec section 13).
     * sort=lowest_price (default) | highest_price
     */
    @GET
    @Path("/{id}/offers")
    public List<OfferDto> offers(@PathParam("id") UUID id,
                                  @QueryParam("sort") @DefaultValue("lowest_price") String sort) {
        Product p = Product.findById(id);
        if (p == null) throw new NotFoundException("Product not found: " + id);

        List<Offer> offers = Offer.list("product = ?1 and availability != 'OUT_OF_STOCK'", p);

        Comparator<Offer> comparator = "highest_price".equals(sort)
                ? Comparator.comparing((Offer o) -> o.totalPrice).reversed()
                : Comparator.comparing(o -> o.totalPrice); // default: lowest total price first

        return offers.stream()
                .sorted(comparator)
                .map(OfferDto::from)
                .collect(Collectors.toList());
    }

    /** Price history + derived stats for the graph and price index (spec sections 9-11). */
    @GET
    @Path("/{id}/price-history")
    public PriceAnalyticsService.PriceStats priceHistory(@PathParam("id") UUID id,
                                                           @QueryParam("range") @DefaultValue("30d") String range) {
        Product p = Product.findById(id);
        if (p == null) throw new NotFoundException("Product not found: " + id);

        int days = switch (range) {
            case "7d" -> 7;
            case "90d" -> 90;
            case "6m" -> 180;
            case "1y" -> 365;
            case "all" -> Integer.MAX_VALUE / 2;
            default -> 30;
        };

        List<PriceHistory> history = days == Integer.MAX_VALUE / 2
                ? PriceHistory.list("product = ?1 order by recordedAt", p)
                : PriceHistory.list("product = ?1 and recordedAt >= ?2 order by recordedAt",
                    p, java.time.Instant.now().minus(days, java.time.temporal.ChronoUnit.DAYS));

        return analytics.computeStats(history);
    }

    /**
     * /compare (spec section 14): 2-4 products side by side. Pulls current/lowest/
     * average price from price history + live offers, aggregate rating from
     * review_summary (never fabricated - blank when no reviews exist yet, per
     * section 40), and every spec key present on ANY of the compared products so
     * the frontend can render one aligned table and highlight differences.
     */
    @GET
    @Path("/compare")
    public List<CompareProductDto> compare(@QueryParam("ids") List<UUID> ids) {
        if (ids == null || ids.size() < 2 || ids.size() > 4) {
            throw new BadRequestException("Provide 2-4 product ids to compare (spec section 14)");
        }

        return ids.stream().map(id -> {
            Product p = Product.findById(id);
            if (p == null) throw new NotFoundException("Product not found: " + id);

            List<Offer> liveOffers = Offer.list("product = ?1 and availability != 'OUT_OF_STOCK'", p);
            BigDecimal currentPrice = liveOffers.stream().map(o -> o.totalPrice)
                    .min(Comparator.naturalOrder()).orElse(null);
            long merchantCount = liveOffers.stream().map(o -> o.merchant.id).distinct().count();

            List<PriceHistory> allHistory = PriceHistory.list("product = ?1", p);
            PriceAnalyticsService.PriceStats stats = analytics.computeStats(allHistory);

            ReviewSummary summary = ReviewSummary.findById(id);
            Double avgRating = summary != null && summary.averageRating != null
                    ? summary.averageRating.doubleValue() : null;
            Integer reviewCount = summary != null ? summary.reviewCount : null;

            Map<String, String> specs = new LinkedHashMap<>();
            List<ProductSpecification> specRows = ProductSpecification.list("product = ?1", p);
            for (ProductSpecification s : specRows) {
                specs.put(s.specKey, s.specUnit != null ? s.specValue + " " + s.specUnit : s.specValue);
            }

            return new CompareProductDto(p.id, p.title, p.brand != null ? p.brand.name : null,
                    currentPrice, stats.lowest(), stats.average(), (int) merchantCount, avgRating, reviewCount, specs);
        }).collect(Collectors.toList());
    }
}
