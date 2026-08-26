<template>
  <v-container class="py-8" v-if="product">
    <h1 class="text-h5 font-weight-bold mb-4">{{ product.title }}</h1>

    <v-row>
      <v-col cols="12" md="4">
        <v-card variant="outlined" class="pa-4 mb-4">
          <div class="text-caption text-medium-emphasis">Best price</div>
          <div class="text-h4 font-weight-bold text-primary" v-if="offers.length">
            €{{ offers[0].totalPrice.toFixed(2) }}
          </div>

          <div class="d-flex ga-4 mt-4" v-if="priceStats">
            <div>
              <div class="text-caption text-medium-emphasis">Price Index</div>
              <div class="text-h6">{{ priceIndexLabel }}</div>
            </div>
          </div>
        </v-card>
      </v-col>

      <v-col cols="12" md="8">
        <h2 class="text-subtitle-1 font-weight-bold mb-2">Compare prices</h2>
        <v-list>
          <v-list-item v-for="o in offers" :key="o.offerId" :href="o.url" target="_blank">
            <template #prepend>
              <v-avatar size="28"><v-img :src="o.merchantLogoUrl" /></v-avatar>
            </template>
            <v-list-item-title>{{ o.merchantName }}</v-list-item-title>
            <v-list-item-subtitle>
              {{ o.availability }} · updated {{ new Date(o.lastSeenAt).toLocaleDateString() }}
            </v-list-item-subtitle>
            <template #append>
              <div class="text-right">
                <div class="text-body-1 font-weight-bold">€{{ o.totalPrice.toFixed(2) }}</div>
                <div class="text-caption text-medium-emphasis" v-if="o.shippingCost !== null">
                  incl. €{{ o.shippingCost.toFixed(2) }} shipping
                </div>
                <div class="text-caption text-medium-emphasis" v-else>shipping unknown</div>
              </div>
            </template>
          </v-list-item>
        </v-list>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { productsApi, type Product, type Offer, type PriceStats } from '@/api/client'

const route = useRoute()
const product = ref<Product | null>(null)
const offers = ref<Offer[]>([])
const priceStats = ref<PriceStats | null>(null)

const priceIndexLabel = computed(() => {
  if (!priceStats.value?.current || !priceStats.value?.average) return '—'
  const idx = Math.round((priceStats.value.current / priceStats.value.average) * 100)
  return `${idx}`
})

onMounted(async () => {
  const id = route.params.id as string
  const [p, o, h] = await Promise.all([
    productsApi.get(id),
    productsApi.offers(id),
    productsApi.priceHistory(id, '90d')
  ])
  product.value = p.data
  offers.value = o.data
  priceStats.value = h.data
})
</script>
