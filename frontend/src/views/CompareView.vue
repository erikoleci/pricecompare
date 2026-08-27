<template>
  <v-container class="py-8">
    <h1 class="text-h5 font-weight-bold mb-2">Compare products</h1>
    <p class="text-medium-emphasis mb-6">Add 2-4 products to compare price, specs, and ratings side by side.</p>

    <v-row class="mb-6" align="center">
      <v-col cols="12" md="6">
        <v-autocomplete
          v-model="searchQuery"
          v-model:search="searchQuery"
          :items="searchResults"
          item-title="title"
          item-value="productId"
          label="Search a product to add..."
          variant="outlined"
          density="comfortable"
          hide-details
          :disabled="selectedIds.length >= 4"
          no-filter
          @update:search="onSearchInput"
          @update:model-value="addProduct"
        >
          <template #item="{ props: itemProps, item }">
            <v-list-item v-bind="itemProps" :subtitle="item.raw.brandName || undefined" />
          </template>
        </v-autocomplete>
        <p v-if="selectedIds.length >= 4" class="text-caption text-medium-emphasis mt-1">
          Maximum of 4 products (spec section 14).
        </p>
      </v-col>
    </v-row>

    <v-alert v-if="selectedIds.length < 2" type="info" variant="tonal">
      Add at least 2 products to see a comparison.
    </v-alert>

    <v-progress-linear v-else-if="loading" indeterminate class="mb-4" />

    <v-table v-else-if="products.length" class="compare-table">
      <thead>
        <tr>
          <th>Attribute</th>
          <th v-for="p in products" :key="p.productId">
            <div class="d-flex justify-space-between align-center">
              <span>{{ p.title }}</span>
              <v-btn icon="mdi-close" size="x-small" variant="text" @click="removeProduct(p.productId)" />
            </div>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr :class="{ 'highlight-row': differs('currentPrice') }">
          <td class="font-weight-medium">Current price</td>
          <td v-for="p in products" :key="p.productId">
            {{ p.currentPrice !== null ? `€${p.currentPrice.toFixed(2)}` : '—' }}
          </td>
        </tr>
        <tr :class="{ 'highlight-row': differs('lowestPrice') }">
          <td class="font-weight-medium">Lowest price</td>
          <td v-for="p in products" :key="p.productId">
            {{ p.lowestPrice !== null ? `€${p.lowestPrice.toFixed(2)}` : '—' }}
          </td>
        </tr>
        <tr :class="{ 'highlight-row': differs('averagePrice') }">
          <td class="font-weight-medium">Average price</td>
          <td v-for="p in products" :key="p.productId">
            {{ p.averagePrice !== null ? `€${p.averagePrice.toFixed(2)}` : '—' }}
          </td>
        </tr>
        <tr :class="{ 'highlight-row': differs('merchantCount') }">
          <td class="font-weight-medium">Available at</td>
          <td v-for="p in products" :key="p.productId">{{ p.merchantCount }} stores</td>
        </tr>
        <tr :class="{ 'highlight-row': differs('averageRating') }">
          <td class="font-weight-medium">Rating</td>
          <td v-for="p in products" :key="p.productId">
            <span v-if="p.averageRating !== null">★ {{ p.averageRating.toFixed(1) }} ({{ p.reviewCount }})</span>
            <span v-else class="text-disabled">No reviews yet</span>
          </td>
        </tr>
        <tr v-for="key in allSpecKeys" :key="key" :class="{ 'highlight-row': differsSpec(key) }">
          <td class="font-weight-medium text-capitalize">{{ key.replace(/_/g, ' ') }}</td>
          <td v-for="p in products" :key="p.productId">{{ p.specifications[key] ?? '—' }}</td>
        </tr>
      </tbody>
    </v-table>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { productsApi, searchApi } from '@/api/client'
import type { CompareProduct, SearchResult } from '@/api/client'

const route = useRoute()
const router = useRouter()

const selectedIds = ref<string[]>(
  ((route.query.ids as string) || '').split(',').filter(Boolean)
)
const products = ref<CompareProduct[]>([])
const loading = ref(false)

const searchQuery = ref('')
const searchResults = ref<SearchResult[]>([])
let searchDebounce: ReturnType<typeof setTimeout> | undefined

function onSearchInput(text: string) {
  clearTimeout(searchDebounce)
  if (!text || text.length < 2) {
    searchResults.value = []
    return
  }
  searchDebounce = setTimeout(async () => {
    const { data } = await searchApi.search({ q: text })
    searchResults.value = data.filter(r => !selectedIds.value.includes(r.productId))
  }, 250)
}

function addProduct(productId: string | null) {
  if (!productId || selectedIds.value.includes(productId) || selectedIds.value.length >= 4) return
  selectedIds.value = [...selectedIds.value, productId]
  searchQuery.value = ''
  searchResults.value = []
}

function removeProduct(productId: string) {
  selectedIds.value = selectedIds.value.filter(id => id !== productId)
}

const allSpecKeys = computed(() => {
  const keys = new Set<string>()
  products.value.forEach(p => Object.keys(p.specifications).forEach(k => keys.add(k)))
  return Array.from(keys)
})

function differs(field: keyof CompareProduct): boolean {
  const values = products.value.map(p => p[field])
  return new Set(values.map(v => JSON.stringify(v))).size > 1
}

function differsSpec(key: string): boolean {
  const values = products.value.map(p => p.specifications[key] ?? null)
  return new Set(values).size > 1
}

async function loadComparison() {
  router.replace({ query: { ids: selectedIds.value.join(',') || undefined } })
  if (selectedIds.value.length < 2) {
    products.value = []
    return
  }
  loading.value = true
  try {
    const { data } = await productsApi.compare(selectedIds.value)
    products.value = data
  } finally {
    loading.value = false
  }
}

watch(selectedIds, loadComparison, { deep: true })
onMounted(loadComparison)
</script>

<style scoped>
.compare-table th, .compare-table td {
  min-width: 160px;
}
.highlight-row {
  background: rgba(var(--v-theme-primary), 0.06);
}
</style>
