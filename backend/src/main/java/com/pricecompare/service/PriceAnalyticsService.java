package com.pricecompare.service;

import com.pricecompare.entity.PriceHistory;
import jakarta.enterprise.context.ApplicationScoped;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.UUID;

/**
 * Computes price-history derived metrics: min/max/average, price index,
 * price change %, and deal score. Pure calculation layer - no DB writes here.
 *
 * Spec references:
 *  - section 9  Price History Graph
 *  - section 10 Price Index  (currentPrice / historicalAverage * 100)
 *  - section 11 Lowest/Highest/Average
 *  - section 12 Price Change Analytics (7d/30d/90d/365d)
 *  - section 18 Deal Score
 */
@ApplicationScoped
public class PriceAnalyticsService {

    public record PriceStats(
            BigDecimal current,
            BigDecimal lowest,
            BigDecimal highest,
            BigDecimal average,
            Instant lowestDate,
            Instant highestDate
    ) {}

    public record PriceIndex(BigDecimal index, String interpretation) {}

    public PriceStats computeStats(List<PriceHistory> history) {
        if (history.isEmpty()) {
            return new PriceStats(null, null, null, null, null, null);
        }
        PriceHistory current = history.get(history.size() - 1);
        PriceHistory lowestPoint = history.stream()
                .min((a, b) -> a.totalPrice.compareTo(b.totalPrice)).orElseThrow();
        PriceHistory highestPoint = history.stream()
                .max((a, b) -> a.totalPrice.compareTo(b.totalPrice)).orElseThrow();

        BigDecimal sum = history.stream()
                .map(h -> h.totalPrice)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
        BigDecimal average = sum.divide(BigDecimal.valueOf(history.size()), 2, RoundingMode.HALF_UP);

        return new PriceStats(
                current.totalPrice,
                lowestPoint.totalPrice,
                highestPoint.totalPrice,
                average,
                lowestPoint.recordedAt,
                highestPoint.recordedAt
        );
    }

    /** priceIndex = currentPrice / historicalAverage * 100 (spec section 10) */
    public PriceIndex computePriceIndex(BigDecimal currentPrice, BigDecimal historicalAverage) {
        if (historicalAverage == null || historicalAverage.compareTo(BigDecimal.ZERO) == 0) {
            return new PriceIndex(null, "Not enough history");
        }
        BigDecimal index = currentPrice
                .divide(historicalAverage, 4, RoundingMode.HALF_UP)
                .multiply(BigDecimal.valueOf(100))
                .setScale(0, RoundingMode.HALF_UP);

        String interpretation;
        double v = index.doubleValue();
        if (v < 90) interpretation = "Excellent price";
        else if (v <= 97) interpretation = "Good price";
        else if (v <= 103) interpretation = "Normal price";
        else if (v <= 110) interpretation = "Expensive";
        else interpretation = "Very expensive";

        return new PriceIndex(index, interpretation);
    }

    /** % change between the current price and the price `days` ago (spec section 12). Null if no data point that far back. */
    public BigDecimal computePriceChangePercent(List<PriceHistory> history, int days) {
        if (history.isEmpty()) return null;
        Instant cutoff = Instant.now().minus(days, ChronoUnit.DAYS);
        BigDecimal current = history.get(history.size() - 1).totalPrice;

        PriceHistory reference = history.stream()
                .filter(h -> !h.recordedAt.isAfter(cutoff))
                .reduce((first, second) -> second) // last one before/at cutoff
                .orElse(null);
        if (reference == null) return null; // not enough history yet

        BigDecimal refPrice = reference.totalPrice;
        if (refPrice.compareTo(BigDecimal.ZERO) == 0) return null;

        return current.subtract(refPrice)
                .divide(refPrice, 4, RoundingMode.HALF_UP)
                .multiply(BigDecimal.valueOf(100))
                .setScale(2, RoundingMode.HALF_UP);
    }

    /**
     * Deal score 0-100 (spec section 18). Simple, explainable baseline -
     * NOT a black box. Weighs distance from historical average and from
     * all-time low, plus merchant availability.
     */
    public int computeDealScore(BigDecimal currentPrice, BigDecimal historicalAverage,
                                 BigDecimal allTimeLow, int merchantCount) {
        if (historicalAverage == null || historicalAverage.compareTo(BigDecimal.ZERO) == 0) {
            return 50; // neutral - not enough data
        }

        double belowAveragePct = 1 - (currentPrice.doubleValue() / historicalAverage.doubleValue());
        double aboveLowPct = allTimeLow != null && allTimeLow.compareTo(BigDecimal.ZERO) > 0
                ? (currentPrice.doubleValue() / allTimeLow.doubleValue()) - 1
                : 0;

        double score = 70
                + (belowAveragePct * 150)   // being below average pushes score up
                - (aboveLowPct * 100)        // being far above all-time low pulls score down
                + Math.min(merchantCount, 10); // more merchants = more competition = slightly better deal

        return (int) Math.max(0, Math.min(100, Math.round(score)));
    }

    /** "Best time to buy" heuristic based purely on historical data (spec section 26). Never framed as a prediction. */
    public String buyingRecommendation(PriceIndex priceIndex) {
        if (priceIndex.index() == null) return "NORMAL"; // not enough data yet
        double v = priceIndex.index().doubleValue();
        if (v < 95) return "GOOD_TIME"; // green
        if (v <= 105) return "NORMAL";  // yellow
        return "WAIT";                  // red
    }
}
