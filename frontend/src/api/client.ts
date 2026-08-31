import axios from 'axios'

// Render Static Sites can't proxy /api/* to another service the way the
// nginx.conf in this repo does for the Docker deployment path (see
// infra/DEPLOY.md) - so on Render, the frontend has to call the backend's
// full public URL directly. VITE_API_BASE_URL is a build-time env var (set
// it in the Render Static Site's Environment tab, e.g.
// https://pricecompare-jubj.onrender.com/api) - falls back to the relative
// '/api' path for the Docker/nginx deployment, where the proxy handles it.
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || '/api'

export const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 10000
})

export interface Offer {
  offerId: string
  merchantId: string
  merchantName: string
  merchantLogoUrl?: string
  price: number
  shippingCost: number | null
  totalPrice: number
  currency: string
  availability: string
  url: string
  lastSeenAt: string
}

export interface Product {
  id: string
  title: string
  normalizedTitle: string
  description?: string
  status: string
}

export interface PriceStats {
  current: number | null
  lowest: number | null
  highest: number | null
  average: number | null
  lowestDate: string | null
  highestDate: string | null
}

export interface SearchResult {
  productId: string
  title: string
  brandName: string | null
  categoryName: string | null
  categorySlug: string | null
  lowestTotalPrice: number | null
  merchantCount: number
  matchType: 'EAN' | 'GTIN' | 'MPN' | 'SKU' | 'FULLTEXT' | 'FUZZY'
}

export interface CompareProduct {
  productId: string
  title: string
  brandName: string | null
  currentPrice: number | null
  lowestPrice: number | null
  averagePrice: number | null
  merchantCount: number
  averageRating: number | null
  reviewCount: number | null
  specifications: Record<string, string>
}

export interface CategoryFilter {
  key: string
  label: string
  type: 'multi_select' | 'boolean' | 'range'
  source: string
  options?: string[]
}

export interface Category {
  id: string
  slug: string
  name: string
  filterSchema?: { filters: CategoryFilter[] } | string[] | null
}

export const productsApi = {
  list: (params?: Record<string, unknown>) => apiClient.get<Product[]>('/products', { params }),
  get: (id: string) => apiClient.get<Product>(`/products/${id}`),
  offers: (id: string, sort: 'lowest_price' | 'highest_price' = 'lowest_price') =>
    apiClient.get<Offer[]>(`/products/${id}/offers`, { params: { sort } }),
  priceHistory: (id: string, range: '7d' | '30d' | '90d' | '6m' | '1y' | 'all' = '30d') =>
    apiClient.get<PriceStats>(`/products/${id}/price-history`, { params: { range } }),
  compare: (ids: string[]) =>
    apiClient.get<CompareProduct[]>('/products/compare', { params: { ids } })
}

export const searchApi = {
  search: (params: { q: string; category?: string; brand?: string; page?: number; size?: number }) =>
    apiClient.get<SearchResult[]>('/search', { params })
}

export const categoriesApi = {
  list: () => apiClient.get<Category[]>('/categories'),
  get: (slug: string) => apiClient.get<Category>(`/categories/${slug}`)
}

export interface AdminMerchant {
  merchantId: string
  name: string
  domain: string
  status: string
  crawlerEnabled: boolean
  lastSuccessfulCrawl: string | null
  sourceId: string | null
  sourceType: string | null
  baseUrl: string | null
  robotsTxtUrl: string | null
  robotsTxtCheckedAt: string | null
  allowedByRobots: boolean | null
  tosReviewed: boolean
  tosNotes: string | null
  isSupported: boolean
}

export interface ComplianceReviewRequest {
  allowedByRobots?: boolean
  tosReviewed?: boolean
  tosNotes?: string
  approve?: boolean
}

export interface AdminDashboard {
  totalProducts: number
  activeProducts: number
  totalOffers: number
  totalMerchants: number
  activeMerchants: number
  unsupportedMerchants: number
  approvedSources: number
  pendingComplianceReview: number
}

export const adminApi = {
  dashboard: () => apiClient.get<AdminDashboard>('/admin/dashboard'),
  merchants: () => apiClient.get<AdminMerchant[]>('/admin/merchants'),
  updateCompliance: (merchantId: string, body: ComplianceReviewRequest) =>
    apiClient.patch<AdminMerchant>(`/admin/merchants/${merchantId}/compliance`, body),
  reviews: () => apiClient.get<Record<string, unknown>[]>('/admin/reviews'),
  priceDrops: () => apiClient.get<Record<string, unknown>[]>('/admin/price-drops'),
  priceAlerts: () => apiClient.get<Record<string, unknown>[]>('/admin/price-alerts'),
  searches: () => apiClient.get<Record<string, unknown>[]>('/admin/searches'),
  clicks: () => apiClient.get<Record<string, unknown>[]>('/admin/clicks')
}

export const trackingApi = {
  click: (eventType: 'OFFER_CLICK' | 'PRODUCT_VIEW' | 'SEARCH_RESULT_CLICK', productId?: string, offerId?: string) =>
    apiClient.post('/track/click', { eventType, productId, offerId }).catch(() => {
      // tracking must never block the user's actual action (viewing a product, clicking an offer)
    })
}
