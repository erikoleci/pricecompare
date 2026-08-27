package com.pricecompare.dto;

import java.math.BigDecimal;
import java.util.Map;
import java.util.UUID;

/** One column of the /compare table (spec section 14). */
public class CompareProductDto {
    public UUID productId;
    public String title;
    public String brandName;
    public BigDecimal currentPrice;   // cheapest current total price across merchants
    public BigDecimal lowestPrice;    // all-time low, from price_history
    public BigDecimal averagePrice;   // all-time average, from price_history
    public int merchantCount;
    public Double averageRating;      // null if no reviews yet
    public Integer reviewCount;
    /** spec_key -> spec_value, e.g. "display" -> "6.9 in", "ram" -> "12 GB" - the
     * frontend renders one table row per key that appears in ANY compared
     * product, so differing keys across products just show blank cells. */
    public Map<String, String> specifications;

    public CompareProductDto(UUID productId, String title, String brandName, BigDecimal currentPrice,
                              BigDecimal lowestPrice, BigDecimal averagePrice, int merchantCount,
                              Double averageRating, Integer reviewCount, Map<String, String> specifications) {
        this.productId = productId;
        this.title = title;
        this.brandName = brandName;
        this.currentPrice = currentPrice;
        this.lowestPrice = lowestPrice;
        this.averagePrice = averagePrice;
        this.merchantCount = merchantCount;
        this.averageRating = averageRating;
        this.reviewCount = reviewCount;
        this.specifications = specifications;
    }
}
