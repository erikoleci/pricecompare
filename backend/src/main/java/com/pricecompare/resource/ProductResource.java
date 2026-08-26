package com.pricecompare.resource;

import com.pricecompare.dto.OfferDto;
import com.pricecompare.entity.Offer;
import com.pricecompare.entity.PriceHistory;
import com.pricecompare.entity.Product;
import com.pricecompare.service.PriceAnalyticsService;
import jakarta.inject.Inject;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import java.util.Comparator;
import java.util.List;
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
        var query = Product.find("status = 'ACTIVE'");
        return query.page(page, size).list();
        // NOTE: category/brand filtering + dynamic per-category filters (spec section 24)
        // are added once the search module (Phase 5) is in place.
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
}
