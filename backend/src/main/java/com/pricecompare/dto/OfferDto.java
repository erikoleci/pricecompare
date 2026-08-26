package com.pricecompare.dto;

import com.pricecompare.entity.Offer;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/** Flattened offer for the "cheapest -> most expensive" list (spec section 13). */
public class OfferDto {
    public UUID offerId;
    public UUID merchantId;
    public String merchantName;
    public String merchantLogoUrl;
    public BigDecimal price;
    public BigDecimal shippingCost; // null = unknown
    public BigDecimal totalPrice;
    public String currency;
    public String availability;
    public String url;
    public Instant lastSeenAt;

    public static OfferDto from(Offer o) {
        OfferDto dto = new OfferDto();
        dto.offerId = o.id;
        dto.merchantId = o.merchant.id;
        dto.merchantName = o.merchant.name;
        dto.merchantLogoUrl = o.merchant.logoUrl;
        dto.price = o.price;
        dto.shippingCost = o.shippingCost;
        dto.totalPrice = o.totalPrice;
        dto.currency = o.currency;
        dto.availability = o.availability;
        dto.url = o.url;
        dto.lastSeenAt = o.lastSeenAt;
        return dto;
    }
}
