package com.pricecompare.resource;

import jakarta.inject.Inject;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;

import javax.sql.DataSource;
import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.Timestamp;
import java.time.Instant;

/**
 * Records real user interactions (spec sections 21, 28): a product page
 * view, an offer click-through to a merchant, or a search-result click.
 * This is what feeds the admin "Clicks" dashboard section and, eventually,
 * "popular products" ranking (section 31's HIGH-priority crawl tier) - it
 * only ever writes what actually happened, nothing inferred or backfilled.
 */
@Path("/api/track")
@Consumes(MediaType.APPLICATION_JSON)
public class TrackingResource {

    @Inject
    DataSource dataSource;

    public record ClickRequest(String eventType, String productId, String offerId) {}

    @POST
    @Path("/click")
    @Transactional
    public void recordClick(ClickRequest body) throws Exception {
        String type = body.eventType() != null ? body.eventType() : "OFFER_CLICK";
        if (!type.equals("OFFER_CLICK") && !type.equals("PRODUCT_VIEW") && !type.equals("SEARCH_RESULT_CLICK")) {
            throw new BadRequestException("eventType must be OFFER_CLICK, PRODUCT_VIEW, or SEARCH_RESULT_CLICK");
        }
        try (Connection conn = dataSource.getConnection();
             PreparedStatement ps = conn.prepareStatement(
                     "INSERT INTO click_events (product_id, offer_id, event_type, created_at) VALUES (?, ?, ?, ?)")) {
            ps.setObject(1, body.productId() != null ? java.util.UUID.fromString(body.productId()) : null);
            ps.setObject(2, body.offerId() != null ? java.util.UUID.fromString(body.offerId()) : null);
            ps.setString(3, type);
            ps.setTimestamp(4, Timestamp.from(Instant.now()));
            ps.executeUpdate();
        }
    }
}
