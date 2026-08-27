package com.pricecompare.dto;

import java.math.BigDecimal;
import java.util.UUID;

/**
 * One row in a search result list (spec section 23). `matchType` tells the
 * frontend why this product matched, so it can e.g. show "Matched by EAN"
 * for a barcode lookup vs a plain text match.
 */
public class SearchResultDto {
    public UUID productId;
    public String title;
    public String brandName;
    public String categoryName;
    public String categorySlug;
    public BigDecimal lowestTotalPrice; // null if the product currently has no offers
    public int merchantCount;
    public String matchType; // EAN, SKU, FULLTEXT, FUZZY

    public SearchResultDto(UUID productId, String title, String brandName, String categoryName,
                            String categorySlug, BigDecimal lowestTotalPrice, int merchantCount,
                            String matchType) {
        this.productId = productId;
        this.title = title;
        this.brandName = brandName;
        this.categoryName = categoryName;
        this.categorySlug = categorySlug;
        this.lowestTotalPrice = lowestTotalPrice;
        this.merchantCount = merchantCount;
        this.matchType = matchType;
    }
}
