package com.pricecompare.resource;

import com.pricecompare.entity.Merchant;
import jakarta.transaction.Transactional;
import jakarta.ws.rs.*;
import jakarta.ws.rs.core.MediaType;
import java.util.List;
import java.util.UUID;

@Path("/api/merchants")
@Produces(MediaType.APPLICATION_JSON)
@Consumes(MediaType.APPLICATION_JSON)
public class MerchantResource {

    @GET
    public List<Merchant> list(@QueryParam("status") String status) {
        if (status != null) {
            return Merchant.list("status", status);
        }
        return Merchant.listAll();
    }

    @GET
    @Path("/{id}")
    public Merchant get(@PathParam("id") UUID id) {
        Merchant m = Merchant.findById(id);
        if (m == null) throw new NotFoundException("Merchant not found: " + id);
        return m;
    }

    @POST
    @Transactional
    public Merchant create(Merchant merchant) {
        merchant.id = null;
        merchant.persist();
        return merchant;
    }

    @PUT
    @Path("/{id}")
    @Transactional
    public Merchant update(@PathParam("id") UUID id, Merchant payload) {
        Merchant m = Merchant.findById(id);
        if (m == null) throw new NotFoundException("Merchant not found: " + id);
        m.name = payload.name;
        m.domain = payload.domain;
        m.country = payload.country;
        m.currency = payload.currency;
        m.status = payload.status;
        m.crawlerEnabled = payload.crawlerEnabled;
        return m;
    }
}
