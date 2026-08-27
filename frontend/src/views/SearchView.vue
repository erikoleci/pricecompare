<template>
  <v-container class="py-8">
    <v-row>
      <v-col cols="12" md="3">
        <v-text-field
          v-model="query"
          label="Search product, brand, model, EAN..."
          prepend-inner-icon="mdi-magnify"
          variant="outlined"
          density="comfortable"
          hide-details
          class="mb-4"
          @keyup.enter="runSearch"
        />

        <template v-if="filterSchema.length">
          <div class="text-subtitle-2 mb-2">Filters</div>
          <div v-for="filter in filterSchema" :key="filter.key" class="mb-4">
            <template v-if="filter.type === 'boolean'">
              <v-checkbox v-model="activeFilters[filter.key]" :label="filter.label" density="compact" hide-details />
            </template>
            <template v-else>
              <div class="text-caption text-medium-emphasis mb-1">{{ filter.label }}</div>
              <v-chip-group v-if="filter.options" v-model="activeFilters[filter.key]" column>
                <v-chip v-for="opt in filter.options" :key="opt" :value="opt" size="small" filter>{{ opt }}</v-chip>
              </v-chip-group>
              <p v-else class="text-caption text-disabled">
                Options populate from real offer data once crawled.
              </p>
            </template>
          </div>
        </template>
      </v-col>

      <v-col cols="12" md="9">
        <div class="d-flex align-center justify-space-between mb-4">
          <h1 class="text-h5 font-weight-bold">
            {{ query ? `Results for "${query}"` : 'Search' }}
          </h1>
          <v-chip v-if="results.length && matchTypeLabel" size="small" variant="tonal">{{ matchTypeLabel }}</v-chip>
        </div>

        <v-progress-linear v-if="loading" indeterminate class="mb-4" />

        <v-alert v-else-if="searched && !results.length" type="info" variant="tonal" class="mb-4">
          No products matched "{{ query }}" yet. The catalog only has what's been crawled so far.
        </v-alert>

        <v-row>
          <v-col v-for="r in results" :key="r.productId" cols="12" sm="6" lg="4">
            <v-card :to="`/products/${r.productId}`" hover class="pa-4 h-100">
              <div class="text-caption text-medium-emphasis mb-1">
                {{ r.brandName || '' }} <span v-if="r.categoryName">· {{ r.categoryName }}</span>
              </div>
              <div class="font-weight-medium mb-2">{{ r.title }}</div>
              <div v-if="r.lowestTotalPrice !== null" class="text-h6">
                From €{{ r.lowestTotalPrice.toFixed(2) }}
              </div>
              <div v-else class="text-body-2 text-disabled">No offers yet</div>
              <div class="text-caption text-medium-emphasis mt-1">
                {{ r.merchantCount }} store{{ r.merchantCount === 1 ? '' : 's' }}
              </div>
            </v-card>
          </v-col>
        </v-row>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { searchApi, categoriesApi } from '@/api/client'
import type { SearchResult, CategoryFilter } from '@/api/client'

const route = useRoute()
const router = useRouter()

const query = ref((route.query.q as string) || '')
const categorySlug = ref((route.query.category as string) || '')
const results = ref<SearchResult[]>([])
const loading = ref(false)
const searched = ref(false)
const filterSchema = ref<CategoryFilter[]>([])
const activeFilters = reactive<Record<string, unknown>>({})

const matchTypeLabel = ref('')

async function loadFilterSchema() {
  filterSchema.value = []
  if (!categorySlug.value) return
  try {
    const { data } = await categoriesApi.get(categorySlug.value)
    const schema = data.filterSchema
    if (schema && typeof schema === 'object' && !Array.isArray(schema) && 'filters' in schema) {
      filterSchema.value = schema.filters
    }
  } catch {
    // category has no typed filter schema yet (still the plain-array seed) - fine, just show none
    filterSchema.value = []
  }
}

async function runSearch() {
  if (!query.value.trim()) {
    results.value = []
    searched.value = false
    return
  }
  loading.value = true
  searched.value = true
  router.replace({ query: { q: query.value, category: categorySlug.value || undefined } })
  try {
    const { data } = await searchApi.search({ q: query.value, category: categorySlug.value || undefined })
    results.value = data
    const labels: Record<SearchResult['matchType'], string> = {
      EAN: 'Matched by EAN', GTIN: 'Matched by GTIN', MPN: 'Matched by MPN', SKU: 'Matched by SKU',
      FULLTEXT: '', FUZZY: 'Showing close matches'
    }
    matchTypeLabel.value = data[0] ? labels[data[0].matchType] : ''
  } finally {
    loading.value = false
  }
}

watch(categorySlug, loadFilterSchema)

onMounted(() => {
  loadFilterSchema()
  if (query.value) runSearch()
})
</script>
