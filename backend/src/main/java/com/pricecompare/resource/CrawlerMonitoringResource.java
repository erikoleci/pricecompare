package com.pricecompare.resource;

import com.pricecompare.entity.CrawlerRun;
import com.pricecompare.entity.Merchant;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Map;
import java.util.UUID;

/**
 * Crawler + admin monitoring dashboard data (spec sections 28-29).
 * Read-only for now - crawler_runs/crawler_errors rows are written by the
 * Python crawler's storage layer, not created through this API.
 */
@Path("/api/admin/crawler")
@Produces(MediaType.APPLICATION_JSON)
public class CrawlerMonitoringResource {

    /** Per-merchant crawler status table (spec section 29). */
    @GET
    @Path("/runs")
    public List<CrawlerRun> recentRuns(@QueryParam("merchantId") UUID merchantId,
                                        @QueryParam("limit") @DefaultValue("50") int limit) {
        if (merchantId != null) {
            Merchant m = Merchant.findById(merchantId);
            if (m == null) throw new NotFoundException("Merchant not found: " + merchantId);
            return CrawlerRun.find("merchant = ?1 order by startedAt desc", m).page(0, limit).list();
        }
        return CrawlerRun.findAll().page(0, limit).list();
    }

    /** Today's rollup for the admin dashboard (spec section 28). */
    @GET
    @Path("/summary")
    public Map<String, Object> summary() {
        Instant since = Instant.now().truncatedTo(ChronoUnit.DAYS);

        long runsToday = CrawlerRun.count("startedAt >= ?1", since);
        long successToday = CrawlerRun.count("startedAt >= ?1 and status = 'SUCCESS'", since);
        long failedToday = CrawlerRun.count("startedAt >= ?1 and status = 'FAILED'", since);

        Long productsCrawledToday = CrawlerRun.find("startedAt >= ?1", since).stream()
                .mapToLong(r -> ((CrawlerRun) r).productsFound == null ? 0 : ((CrawlerRun) r).productsFound)
                .sum();
        Long pricesChangedToday = CrawlerRun.find("startedAt >= ?1", since).stream()
                .mapToLong(r -> ((CrawlerRun) r).pricesChanged == null ? 0 : ((CrawlerRun) r).pricesChanged)
                .sum();

        double successRate = runsToday == 0 ? 0.0 : (double) successToday / runsToday * 100;

        return Map.of(
                "runsToday", runsToday,
                "successToday", successToday,
                "failedToday", failedToday,
                "crawlerSuccessRate", Math.round(successRate * 10) / 10.0,
                "productsCrawledToday", productsCrawledToday,
                "pricesChangedToday", pricesChangedToday
        );
    }
}
