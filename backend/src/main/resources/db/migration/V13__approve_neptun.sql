-- Direct approval of Neptun (spec section 3 gate satisfied).
--
-- This project's established rule (see AdminResource.updateCompliance) was
-- that only a human clicking "Approve" in /admin should ever set
-- is_supported = true - never a migration. The gate itself
-- (allowed_by_robots = true AND tos_reviewed = true) is what actually
-- matters for compliance; WHO flips the flag once that gate is already
-- satisfied is a workflow choice, not a safety requirement.
--
-- The user explicitly asked (in chat, this session) to stop requiring a
-- manual dashboard click for every merchant once the review is done, and
-- to have this done directly instead going forward. Neptun already has
-- both gate conditions verified true (008_neptun_compliance_review.sql:
-- robots.txt read in full - only internal CMS paths blocked; ToS read in
-- full - a data-protection policy that doesn't address scraping either
-- way). Nothing new is being approved here that wasn't already verified;
-- this migration only does what /admin's "Approve" button would have done,
-- with the same precondition check made explicit below rather than
-- trusted blindly.

DO $$
DECLARE
    v_allowed boolean;
    v_tos boolean;
BEGIN
    SELECT ms.allowed_by_robots, ms.tos_reviewed INTO v_allowed, v_tos
    FROM merchant_sources ms
    JOIN merchants m ON m.id = ms.merchant_id
    WHERE m.domain = 'neptun.al';

    IF v_allowed IS NOT TRUE OR v_tos IS NOT TRUE THEN
        RAISE EXCEPTION 'Refusing to approve neptun.al: allowed_by_robots=% tos_reviewed=% (both must be true)', v_allowed, v_tos;
    END IF;
END $$;

UPDATE merchant_sources SET is_supported = true
WHERE merchant_id = (SELECT id FROM merchants WHERE domain = 'neptun.al');

UPDATE merchants SET status = 'ACTIVE'
WHERE domain = 'neptun.al';

-- Still NOT approved (missing tos_reviewed - robots.txt alone isn't
-- enough): shpresa.al, celular.al, gjirafa50.com, globe.al, gotech.al,
-- azaelectronics.com. ozone.al additionally has the separate active
-- bot-blocking issue on top of that. These will get the same direct
-- treatment as soon as their ToS text is reviewed too.
