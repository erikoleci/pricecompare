<template>
  <v-container class="py-12">
    <div class="text-center mb-10">
      <h1 class="text-h3 font-weight-bold mb-2">Find the best price.</h1>
      <p class="text-body-1 text-medium-emphasis mb-6">
        Search thousands of electronics from multiple stores.
      </p>
      <v-text-field
        v-model="query"
        placeholder="Search product, brand, model, EAN..."
        prepend-inner-icon="mdi-magnify"
        variant="solo"
        density="comfortable"
        max-width="640"
        class="mx-auto"
        style="max-width: 640px"
        @keyup.enter="search"
      />
    </div>

    <v-row class="mb-10">
      <v-col v-for="cat in categories" :key="cat.slug" cols="6" sm="3" md="3">
        <v-card variant="tonal" class="text-center pa-4" hover :to="`/search?category=${cat.slug}`">
          <v-icon :icon="cat.icon" size="32" class="mb-2" />
          <div class="text-body-2">{{ cat.name }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h2 class="text-h5 font-weight-bold mb-4">Today's Best Deals</h2>
    <p class="text-medium-emphasis">Populates once the crawler + deal score pipeline is live (Phase 4/6).</p>
  </v-container>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const query = ref('')

const categories = [
  { slug: 'smartphones', name: 'Smartphones', icon: 'mdi-cellphone' },
  { slug: 'laptops', name: 'Laptops', icon: 'mdi-laptop' },
  { slug: 'tvs', name: 'TV', icon: 'mdi-television' },
  { slug: 'gaming', name: 'Gaming', icon: 'mdi-controller-classic' },
  { slug: 'smartwatch', name: 'Smartwatch', icon: 'mdi-watch' },
  { slug: 'monitors', name: 'Monitors', icon: 'mdi-monitor' },
  { slug: 'audio', name: 'Audio', icon: 'mdi-headphones' },
  { slug: 'pc-components', name: 'PC Components', icon: 'mdi-expansion-card' }
]

function search() {
  router.push({ path: '/search', query: { q: query.value } })
}
</script>
