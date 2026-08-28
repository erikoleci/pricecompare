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

    <v-table v-else density="comfortable">
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
  </v-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { adminApi } from '@/api/client'
import type { AdminMerchant, AdminDashboard } from '@/api/client'

const merchants = ref<AdminMerchant[]>([])
const dashboard = ref<AdminDashboard | null>(null)
const loading = ref(false)

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
