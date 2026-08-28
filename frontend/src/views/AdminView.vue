<template>
  <v-container class="py-8">
    <h1 class="text-h5 font-weight-bold mb-6">Admin</h1>

    <v-row class="mb-6">
      <v-col cols="6" sm="3" v-for="card in summaryCards" :key="card.label">
        <v-card class="pa-4" variant="tonal">
          <div class="text-caption text-medium-emphasis">{{ card.label }}</div>
          <div class="text-h5 font-weight-bold">{{ card.value }}</div>
        </v-card>
      </v-col>
    </v-row>

    <h2 class="text-h6 font-weight-bold mb-2">Merchants &amp; compliance review</h2>
    <p class="text-body-2 text-medium-emphasis mb-4">
      Per spec section 3, a merchant only becomes crawlable after a human confirms robots.txt allows it
      AND the ToS has been reviewed. Neither happens automatically here.
    </p>

    <v-progress-linear v-if="loading" indeterminate class="mb-4" />

    <v-table v-else density="comfortable" class="mb-8">
      <thead>
        <tr>
          <th>Merchant</th>
          <th>Domain</th>
          <th>Status</th>
          <th>robots.txt</th>
          <th>ToS</th>
          <th>Supported</th>
          <th>Notes</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="m in merchants" :key="m.merchantId">
          <td class="font-weight-medium">{{ m.name }}</td>
          <td><a :href="`https://${m.domain}`" target="_blank" rel="noopener">{{ m.domain }}</a></td>
          <td><v-chip size="small" :color="m.status === 'ACTIVE' ? 'success' : 'default'" variant="tonal">{{ m.status }}</v-chip></td>
          <td>
            <v-chip v-if="m.allowedByRobots === true" size="small" color="success" variant="tonal">Allowed</v-chip>
            <v-chip v-else-if="m.allowedByRobots === false" size="small" color="error" variant="tonal">Disallowed</v-chip>
            <span v-else class="text-disabled">Not checked</span>
          </td>
          <td>
            <v-icon v-if="m.tosReviewed" icon="mdi-check-circle" color="success" size="small" />
            <span v-else class="text-disabled">Not reviewed</span>
          </td>
          <td>
            <v-chip size="small" :color="m.isSupported ? 'success' : 'default'" variant="tonal">
              {{ m.isSupported ? 'Yes' : 'No' }}
            </v-chip>
          </td>
          <td class="text-caption" style="max-width: 320px; white-space: normal;">{{ m.tosNotes || '—' }}</td>
          <td>
            <v-btn
              v-if="!m.isSupported && m.allowedByRobots === true && m.tosReviewed"
              size="small" color="success" variant="tonal"
              @click="approve(m)"
            >
              Approve
            </v-btn>
            <v-btn
              v-else-if="m.isSupported"
              size="small" color="error" variant="text"
              @click="revoke(m)"
            >
              Revoke
            </v-btn>
          </td>
        </tr>
      </tbody>
    </v-table>

    <h2 class="text-h6 font-weight-bold mb-2">Activity (spec section 28)</h2>
    <v-tabs v-model="activityTab" class="mb-4">
      <v-tab value="reviews">Reviews</v-tab>
      <v-tab value="priceDrops">Price Drops</v-tab>
      <v-tab value="priceAlerts">Price Alerts</v-tab>
      <v-tab value="searches">Searches</v-tab>
      <v-tab value="clicks">Clicks</v-tab>
    </v-tabs>

    <v-window v-model="activityTab">
      <v-window-item value="reviews">
        <EmptyOrTable :rows="activity.reviews" empty-text="No reviews yet - never fabricated (spec section 40)." />
      </v-window-item>
      <v-window-item value="priceDrops">
        <EmptyOrTable :rows="activity.priceDrops" empty-text="No price drops detected yet." />
      </v-window-item>
      <v-window-item value="priceAlerts">
        <EmptyOrTable :rows="activity.priceAlerts" empty-text="No price alerts set yet." />
      </v-window-item>
      <v-window-item value="searches">
        <EmptyOrTable :rows="activity.searches" empty-text="No searches logged yet." />
      </v-window-item>
      <v-window-item value="clicks">
        <EmptyOrTable :rows="activity.clicks" empty-text="No clicks tracked yet." />
      </v-window-item>
    </v-window>
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, h } from 'vue'
import { adminApi } from '@/api/client'
import type { AdminMerchant, AdminDashboard } from '@/api/client'

const merchants = ref<AdminMerchant[]>([])
const dashboard = ref<AdminDashboard | null>(null)
const loading = ref(false)
const activityTab = ref('reviews')

const activity = ref<Record<string, Record<string, unknown>[]>>({
  reviews: [], priceDrops: [], priceAlerts: [], searches: [], clicks: []
})

// EmptyOrTable: tiny inline renderless-ish helper component so five near-identical
// generic tables (different columns each) don't need five near-duplicate templates.
const EmptyOrTable = {
  props: { rows: { type: Array, required: true }, emptyText: { type: String, required: true } },
  setup(props: { rows: Record<string, unknown>[]; emptyText: string }) {
    return () => {
      if (!props.rows.length) {
        return h('p', { class: 'text-body-2 text-medium-emphasis pa-4' }, props.emptyText)
      }
      const columns = Object.keys(props.rows[0])
      return h('table', { class: 'v-table__wrapper', style: 'width:100%; font-size: 0.875rem;' }, [
        h('thead', h('tr', columns.map(c => h('th', { class: 'text-left pa-2' }, c)))),
        h('tbody', props.rows.map((row, i) =>
          h('tr', { key: i }, columns.map(c => h('td', { class: 'pa-2' }, String(row[c] ?? '—'))))
        ))
      ])
    }
  }
}

const summaryCards = computed(() => {
  if (!dashboard.value) return []
  const d = dashboard.value
  return [
    { label: 'Products', value: d.totalProducts },
    { label: 'Offers', value: d.totalOffers },
    { label: 'Merchants', value: d.totalMerchants },
    { label: 'Pending review', value: d.pendingComplianceReview }
  ]
})

async function load() {
  loading.value = true
  try {
    const [merchantsRes, dashboardRes] = await Promise.all([adminApi.merchants(), adminApi.dashboard()])
    merchants.value = merchantsRes.data
    dashboard.value = dashboardRes.data
  } finally {
    loading.value = false
  }
}

async function loadActivityTab(tab: string) {
  const loaders: Record<string, () => Promise<Record<string, unknown>[]>> = {
    reviews: async () => (await adminApi.reviews()).data,
    priceDrops: async () => (await adminApi.priceDrops()).data,
    priceAlerts: async () => (await adminApi.priceAlerts()).data,
    searches: async () => (await adminApi.searches()).data,
    clicks: async () => (await adminApi.clicks()).data
  }
  if (loaders[tab]) activity.value[tab] = await loaders[tab]()
}

watch(activityTab, loadActivityTab, { immediate: true })

async function approve(m: AdminMerchant) {
  const { data } = await adminApi.updateCompliance(m.merchantId, { approve: true })
  Object.assign(m, data)
}

async function revoke(m: AdminMerchant) {
  const { data } = await adminApi.updateCompliance(m.merchantId, { approve: false })
  Object.assign(m, data)
}

onMounted(load)
</script>
