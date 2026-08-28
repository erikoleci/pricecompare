package com.pricecompare.dto;

/**
 * Body for PATCH /api/admin/merchants/{id}/compliance - what a human records
 * after actually reading robots.txt and the ToS (spec section 3). Every
 * field is optional so a partial update (e.g. "just recording I read
 * robots.txt and it disallows us") doesn't require re-sending everything.
 */
public class ComplianceReviewRequest {
    public Boolean allowedByRobots;
    public Boolean tosReviewed;
    public String tosNotes;
    /** Only meaningful when allowedByRobots=true AND tosReviewed=true - the resource
     * itself still won't set is_supported=true unless both of those hold. */
    public Boolean approve;
}
